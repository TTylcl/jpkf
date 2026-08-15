"""
dal/query/schedule_query_service.py
排课查询服务 —— Agent 驱动的灵活查询

核心场景：
- 家长："今天什么时候上课" → parent → student → course → schedule
- 老师："我周三有什么课"
- 教务："这门课排了哪些时间"
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from sqlalchemy.orm import aliased

from dal.models.schedule_model import Schedule
from dal.models.course_model import Course
from dal.models.user_model import User
from dal.models.parent_student_model import ParentStudent
from dal.models.student_schedule_model import StudentSchedule
from dal.models.enums import ScheduleActiveStatus
from dal.query.base_query_service import BaseQueryService
from dal.query import PageResult


# ============================================================
# 过滤器
# ============================================================

# 每个排课时段最大容纳学生数
MAX_STUDENTS_PER_SLOT = 2


@dataclass
class ScheduleFilters:
    """排课查询过滤器"""
    student_id: int | None = None        # 查某个学生的课表
    parent_id: int | None = None         # 查某家长所有孩子的课表
    teacher_id: int | None = None
    course_id: int | None = None
    day_of_week: int | None = None       # 1=周一 ... 7=周日
    start_after: time | None = None
    start_before: time | None = None
    available_only: bool = False         # 只返回未满员的时段（student_count < 上限）


# ============================================================
# QueryService
# ============================================================

class ScheduleQueryService(BaseQueryService):
    """排课查询服务"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    # ── 统一查询入口 ──

    async def query_schedules(
        self,
        filters: ScheduleFilters | None = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str | None = None,
    ) -> PageResult:
        """Agent 查询排课的唯一入口，返回 ScheduleItem 列表"""
        from schemas.schedule_schemas import ScheduleItem
        filters = filters or ScheduleFilters()
        stmt = self._build_query(filters)
        stmt = self._apply_ordering(stmt, order_by)

        # count
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # paginate
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        rows = result.mappings().all()

        items = [
            ScheduleItem(
                schedule_id=row["id"],
                course_id=row["course_id"],
                course_name=row.get("course_name", "") or "",
                teacher_id=row["teacher_id"],
                teacher_name=row.get("teacher_name", "") or "",
                student_names=row.get("student_names") or "",
                student_count=row.get("student_count") or 0,
                day_of_week=row["day_of_week"],
                start_time=str(row["start_time"]),
                end_time=str(row["end_time"]),
                classroom=row["classroom"],
            )
            for row in rows
        ]

        return PageResult(items=items, total=total, page=page, page_size=page_size)

    # ── SQL 构建 ──

    def _build_query(self, f: ScheduleFilters) -> Select:
        """
        构建查询。三个路径：

        ① 学生已排路径（查已分配的课）：student_id/parent_id 且 available_only=False
           → INNER JOIN StudentSchedule，只返回该学生已被分配的具体时段
        ② 空位查询路径（查可加入的空位）：available_only=True
           → 非学生路径 + 容量过滤，查所有未满员时段
           → 如果同时传了 student_id，通过 StudentCourse 过滤该学生已报名的课程
        ③ 管理员路径（查所有排课）：无 student/parent 过滤且 available_only=False
           → 查所有排课，含学生聚合信息
        """
        from dal.models.student_course_model import StudentCourse

        # ── 学生聚合子查询：每个排课有哪些学生 ──
        StudentUser = aliased(User)
        student_sub = (
            select(
                StudentSchedule.schedule_id,
                func.string_agg(
                    StudentUser.real_name, ", "
                ).label("student_names"),
                func.count(StudentSchedule.student_id).label("student_count"),
            )
            .select_from(StudentSchedule)
            .join(StudentUser, StudentSchedule.student_id == StudentUser.user_id)
            .where(StudentSchedule.deleted_at.is_(None))
            .group_by(StudentSchedule.schedule_id)
        ).subquery("student_agg")

        # ── 公共 SELECT 列 ──
        select_cols = [
            Schedule.id,
            Schedule.course_id,
            Course.course_name,
            Schedule.teacher_id,
            User.real_name.label("teacher_name"),
            student_sub.c.student_names,
            student_sub.c.student_count,
            Schedule.day_of_week,
            Schedule.start_time,
            Schedule.end_time,
            Schedule.classroom,
        ]

        has_student_filter = f.student_id is not None or f.parent_id is not None

        # ── 路径 ①：查已分配排课（学生/家长看自己的课表）──
        if has_student_filter and not f.available_only:
            stmt = (
                select(*select_cols)
                .select_from(Schedule)
                .join(Course, Schedule.course_id == Course.course_id, isouter=True)
                .join(User, Schedule.teacher_id == User.user_id, isouter=True)
                .outerjoin(student_sub, student_sub.c.schedule_id == Schedule.id)
                .join(
                    StudentSchedule,
                    (StudentSchedule.schedule_id == Schedule.id)
                    & (StudentSchedule.deleted_at.is_(None)),
                )
                .where(
                    Schedule.deleted_at.is_(None),
                    Schedule.status == ScheduleActiveStatus.ACTIVE.value,
                )
            )
            if f.parent_id is not None:
                student_filter = (
                    select(ParentStudent.student_id)
                    .where(ParentStudent.parent_id == f.parent_id, ParentStudent.deleted_at.is_(None))
                )
                stmt = stmt.where(StudentSchedule.student_id.in_(student_filter))
            elif f.student_id is not None:
                stmt = stmt.where(StudentSchedule.student_id == f.student_id)

        else:
            # ── 路径 ②+③：管理员查所有 / 家长查空位（available_only=True）──
            stmt = (
                select(*select_cols)
                .select_from(Schedule)
                .join(Course, Schedule.course_id == Course.course_id, isouter=True)
                .join(User, Schedule.teacher_id == User.user_id, isouter=True)
                .outerjoin(student_sub, student_sub.c.schedule_id == Schedule.id)
                .where(
                    Schedule.deleted_at.is_(None),
                    Schedule.status == ScheduleActiveStatus.ACTIVE.value,
                )
            )

            # ── available_only 时按学生已报名课程过滤（子查询方式，避免额外 DB 往返）──
            if f.available_only and has_student_filter:
                # 解析目标学生 ID → 子查询查出他们报名的课程
                if f.parent_id is not None:
                    target_students_sub = (
                        select(ParentStudent.student_id)
                        .where(ParentStudent.parent_id == f.parent_id, ParentStudent.deleted_at.is_(None))
                    ).subquery("target_students")
                    enrolled_course_sub = (
                        select(StudentCourse.course_id)
                        .where(
                            StudentCourse.student_id.in_(select(target_students_sub.c.student_id)),
                            StudentCourse.status == "active",
                            StudentCourse.deleted_at.is_(None),
                        )
                    ).subquery("enrolled_courses")
                elif f.student_id is not None:
                    enrolled_course_sub = (
                        select(StudentCourse.course_id)
                        .where(
                            StudentCourse.student_id == f.student_id,
                            StudentCourse.status == "active",
                            StudentCourse.deleted_at.is_(None),
                        )
                    ).subquery("enrolled_courses")
                else:
                    enrolled_course_sub = None

                if enrolled_course_sub is not None:
                    stmt = stmt.where(
                        Schedule.course_id.in_(select(enrolled_course_sub.c.course_id))
                    )

        # ── 容量过滤：只返回未满员的时段 ──
        if f.available_only:
            stmt = stmt.where(
                func.coalesce(student_sub.c.student_count, 0) < MAX_STUDENTS_PER_SLOT
            )

        # ── 直接过滤 Schedule 字段 ──
        if f.teacher_id is not None:
            stmt = stmt.where(Schedule.teacher_id == f.teacher_id)

        if f.course_id is not None:
            stmt = stmt.where(Schedule.course_id == f.course_id)

        if f.day_of_week is not None:
            stmt = stmt.where(Schedule.day_of_week == f.day_of_week)

        if f.start_after is not None:
            stmt = stmt.where(Schedule.start_time >= f.start_after)

        if f.start_before is not None:
            stmt = stmt.where(Schedule.start_time <= f.start_before)

        return stmt

    # ── 排序 ──

    def _apply_ordering(self, stmt: Select, order_by: str | None) -> Select:
        if not order_by:
            return stmt.order_by(Schedule.day_of_week.asc(), Schedule.start_time.asc())
        return BaseQueryService._apply_ordering(stmt, Schedule, order_by)

    # ── 快捷方法：今天的课 ──

    async def get_today_schedules(self, student_id: int) -> PageResult:
        """查某个学生今天的课（Agent 快捷入口）"""
        from datetime import datetime
        today = datetime.now().isoweekday()
        return await self.query_schedules(
            filters=ScheduleFilters(student_id=student_id, day_of_week=today)
        )

    async def get_today_schedules_for_parent(self, parent_id: int) -> PageResult:
        """查某家长所有孩子今天的课（Agent 快捷入口）"""
        from datetime import datetime
        today = datetime.now().isoweekday()
        return await self.query_schedules(
            filters=ScheduleFilters(parent_id=parent_id, day_of_week=today)
        )
