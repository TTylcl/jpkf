"""
time: 2023/10/23 10:04

dal/query/student_course_query_service.py
学生选课查询服务 —— Agent 驱动的灵活查询

核心场景：
- 家长："我孩子报了哪些课" → parent_id → student_id → StudentCourse
- 老师："这门课有哪些学生" → course_id → StudentCourse
- 教务："最近有多少新选课" → enrolled_after → StudentCourse
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime  import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from dal.models.student_course_model import StudentCourse
from dal.models.enums import StudentCourseStatus
from dal.query.base_query_service import BaseQueryService
from dal.query import PageResult
#-----------------------------------------------------------------------------------------------------------------------
#过滤器
#-----------------------------------------------------------------------------------------------------------------------
@dataclass
class StudentCourseFilters:
    #学生选课查询过滤器
    student_id: int | None = None #查某个学生的选课记录
    course_id: int | None = None #查某门课的选课记录
    status: StudentCourseStatus | None = None #查某个状态的选课记录
    enrolled_after: datetime | None = None #查某个时间之后的选课记录
    enrolled_before: datetime | None = None #查某个时间之前的选课记录

# ==============================================================
# QueryService
# ==============================================================
class StudentCourseQueryService(BaseQueryService):
    """学生选课查询服务"""
    def __init__(self, session: AsyncSession):
        super().__init__(session)
    # ── 统一查询入口 ──
    async def query_student_courses(
            self,
            filters: StudentCourseFilters | None = None,
            page: int = 1,
            page_size: int = 20,
            order_by: str | None = None,
        ) -> PageResult:
        """Agent查询学生选课记录，支持灵活过滤、分页和排序"""
        filters = filters or StudentCourseFilters()
        stmt = self._build_query(filters)
        stmt = self._apply_ordering(stmt, StudentCourse, order_by)
        return await self._paginate(stmt, page, page_size)
    # ── 内部构建查询 ──
    def _build_query(self, filters: StudentCourseFilters) -> Select:
        """根据过滤器构建 SELECT 语句（预加载课程信息）"""
        stmt = select(StudentCourse).where(StudentCourse.deleted_at.is_(None)) # 软删过滤
        stmt = stmt.options(selectinload(StudentCourse.course))  # ✅ 预加载课程名称等信息
        if filters.student_id is not None:
            stmt = stmt.where(StudentCourse.student_id == filters.student_id)
        if filters.course_id is not None:
            stmt = stmt.where(StudentCourse.course_id == filters.course_id)
        if filters.status is not None:
            stmt = stmt.where(StudentCourse.status == filters.status.value)
        if filters.enrolled_after is not None:
            stmt = stmt.where(StudentCourse.enrolled_at >= filters.enrolled_after) #
        if filters.enrolled_before is not None:
            stmt = stmt.where(StudentCourse.enrolled_at <= filters.enrolled_before) #

        return stmt
