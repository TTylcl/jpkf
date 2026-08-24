"""
service/schedule_service.py
排课 Service —— AI Agent 工具层
"""

from datetime import time as dt_time

from core.context import CTX
from core.service.decorators import tool, ToolMeta
from core.service.utils import get_dao
from core.service.models import ServiceResult
from dal.dao.schedule_dao import ScheduleDao
from dal.dao.course_dao import CourseDao
from dal.dao.student_course_dao import StudentCourseDao
from dal.query.schedule_query_service import ScheduleQueryService, ScheduleFilters


class ScheduleService:
    resource = "schedule"
    dao_class = ScheduleDao

    # ==================== 查询 ====================

    @tool(ToolMeta(
        name="query_schedules",
        description="灵活查询排课。支持按家长/学生/教师/课程/星期几/时间段组合过滤。"
                    "不传任何过滤条件=查所有排课，不传day_of_week=查整周每天。默认按星期+时间升序排列。"
                    "available_only=true 只返回未满员（少于2人）的已有排课时段（管理员视角用）。",
        parameters={
            "parent_id":      {"type": "integer", "description": "家长 ID（查所有孩子的课）", "default": None},
            "student_id":     {"type": "integer", "description": "学生 ID", "default": None},
            "teacher_id":     {"type": "integer", "description": "教师 ID", "default": None},
            "course_id":      {"type": "integer", "description": "课程 ID", "default": None},
            "day_of_week":    {"type": "integer", "description": "星期几：1=周一...7=周日", "default": None},
            "start_after":    {"type": "string",  "description": "开始时间不早于（HH:MM）", "default": None},
            "start_before":   {"type": "string",  "description": "开始时间不晚于（HH:MM）", "default": None},
            "available_only": {"type": "boolean", "description": "家长查空余时段时传 true，只返回未满员（<2人）的时段", "default": False},
            "page":           {"type": "integer", "default": 1},
            "page_size":      {"type": "integer", "default": 20},
        },
        require_permission=True,
    ))
    async def query_schedules(
        self,
        ctx: CTX,
        parent_id: int | None = None,
        student_id: int | None = None,
        teacher_id: int | None = None,
        course_id: int | None = None,
        day_of_week: int | None = None,
        start_after: str | None = None,
        start_before: str | None = None,
        available_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> ServiceResult:
        qs = ScheduleQueryService(ctx.session)

        filters = ScheduleFilters(
            parent_id=parent_id,
            student_id=student_id,
            teacher_id=teacher_id,
            course_id=course_id,
            day_of_week=day_of_week,
            start_after=_parse_time(start_after),
            start_before=_parse_time(start_before),
            available_only=available_only,
        )

        result = await qs.query_schedules(filters, page=page, page_size=page_size)
        return ServiceResult.ok(data=result, trace_id=ctx.trace_id)

    @tool(ToolMeta(
        name="get_today_schedules",
        description="查询指定日期的排课。不传任何参数返回今天全部排课（管理员用），可指定家长/学生/教师过滤。day_of_week 不传默认今天",
        parameters={
            "parent_id":  {"type": "integer", "description": "家长 ID（可选）", "default": None},
            "student_id": {"type": "integer", "description": "学生 ID（可选）", "default": None},
            "teacher_id": {"type": "integer", "description": "教师 ID（可选）", "default": None},
            "day_of_week": {"type": "integer", "description": "星期几：1=周一...7=周日，默认今天", "default": None},
        },
        require_permission=True,
    ))
    async def get_today_schedules(
        self,
        ctx: CTX,
        parent_id: int | None = None,
        student_id: int | None = None,
        teacher_id: int | None = None,
        day_of_week: int | None = None,
    ) -> ServiceResult:
        qs = ScheduleQueryService(ctx.session)

        from datetime import datetime
        target_day = day_of_week if day_of_week else datetime.now().isoweekday()

        if parent_id:
            result = await qs.query_schedules(
                filters=ScheduleFilters(parent_id=parent_id, day_of_week=target_day)
            )
        elif student_id:
            result = await qs.query_schedules(
                filters=ScheduleFilters(student_id=student_id, day_of_week=target_day)
            )
        elif teacher_id:
            result = await qs.query_schedules(
                filters=ScheduleFilters(teacher_id=teacher_id, day_of_week=target_day)
            )
        else:
            # 不传任何参数 → 返回当天所有排课（管理员视角）
            result = await qs.query_schedules(
                filters=ScheduleFilters(day_of_week=target_day)
            )

        return ServiceResult.ok(data=result, trace_id=ctx.trace_id)

    # ==================== 写入 ====================

    @tool(ToolMeta(
        name="create_schedule",
        description="新增排课。系统会自动校验：①课程是否存在 ②教师是否教授该课程 ③该课程是否有已报名的学生。只有校验全部通过才能排课。",
        parameters={
            "course_id":   {"type": "integer", "description": "课程 ID"},
            "teacher_id":  {"type": "integer", "description": "教师 ID"},
            "day_of_week": {"type": "integer", "description": "星期几：1=周一...7=周日"},
            "start_time":  {"type": "string",  "description": "开始时间（HH:MM）"},
            "end_time":    {"type": "string",  "description": "结束时间（HH:MM）"},
            "classroom":   {"type": "string",  "description": "教室（可选）", "default": None},
        },
        require_permission=True,
    ))
    async def create_schedule(
        self,
        ctx: CTX,
        course_id: int,
        teacher_id: int,
        day_of_week: int,
        start_time: str,
        end_time: str,
        classroom: str | None = None,
        _exclude_pre_schedule_id: int | None = None,  # 内部参数：审核预排课时排除自身
    ) -> ServiceResult:
        dao: ScheduleDao = get_dao(ctx, self.dao_class)

        # ① 校验课程是否存在
        course_dao = CourseDao(ctx.session)
        course = await course_dao.get_by_id(course_id)
        if not course:
            return ServiceResult.error(
                message=f"课程#{course_id}不存在", code=404, trace_id=ctx.trace_id
            )

        # ② 校验教师是否教授该课程
        if course.teacher_id != teacher_id:
            # 查教师姓名
            from dal.dao.user_dao import UserDao
            _user_dao = UserDao(ctx.session)
            _req_teacher = await _user_dao.get_by_id(teacher_id)
            _req_teacher_name = _req_teacher.real_name if _req_teacher else f"教师#{teacher_id}"
            _course_teacher = await _user_dao.get_by_id(course.teacher_id)
            _course_teacher_name = _course_teacher.real_name if _course_teacher else f"教师#{course.teacher_id}"
            return ServiceResult.error(
                message=f"{_req_teacher_name}老师不教授「{course.course_name}」，"
                        f"该课程的任教教师为{_course_teacher_name}老师",
                code=403, trace_id=ctx.trace_id,
            )

        # ③ 校验该课程是否有已报名且剩余课时>0的学生（有学生才能排课）
        sc_dao = StudentCourseDao(ctx.session)
        enrolled_students = await sc_dao.list_course_students(course_id)
        valid_students = [
            s for s in enrolled_students
            if s.remaining_lessons and s.remaining_lessons > 0
        ]
        if not valid_students:
            return ServiceResult.error(
                message=f"课程「{course.course_name}」(#{course_id}) 没有已报名且剩余课时>0的学生，无法排课",
                code=409, trace_id=ctx.trace_id,
            )

        # ④ 时间冲突检查（schedule + pre_schedule PENDING 双表）
        if await dao.check_time_conflict(teacher_id, day_of_week, start_time):
            from dal.dao.user_dao import UserDao
            _u = UserDao(ctx.session)
            _t = await _u.get_by_id(teacher_id)
            _tn = _t.real_name if _t else f"教师#{teacher_id}"
            return ServiceResult.error(
                message=f"{_tn}老师在周{day_of_week} {start_time} 已有排课冲突",
                code=409, trace_id=ctx.trace_id,
            )
        # 也查预排课 PENDING 冲突
        from dal.dao.pre_schedule_dao import PreScheduleDao
        from dal.models.enums import PreScheduleStatus
        ps_dao = PreScheduleDao(ctx.session)
        all_pending = await ps_dao.get_pending_reviews()
        check_start = dt_time(*map(int, start_time.split(":")))
        for pre in all_pending:
            # 审核预排课通过时排除自身
            if _exclude_pre_schedule_id is not None and pre.id == _exclude_pre_schedule_id:
                continue
            pre_teacher = pre.preferred_teacher_id or (
                pre.course.teacher_id if pre.course else None
            )
            if pre_teacher != teacher_id:
                continue
            # 结构化时间缺失（老数据/没填期望时间）→ 跳过，不误判
            if pre.day_of_week is None or pre.start_time is None or pre.end_time is None:
                continue
            if pre.day_of_week != day_of_week:
                continue
            if not (check_start >= pre.end_time or check_start < pre.start_time):
                return ServiceResult.error(
                    message=f"该时段与待审核预排课冲突（"
                            f"学生「{pre.student.real_name if pre.student else f'ID:{pre.student_id}'}」，"
                            f"课程「{pre.course.course_name if pre.course else f'ID:{pre.course_id}'}」）",
                    code=409, trace_id=ctx.trace_id,
                )

        schedule = await dao.create_schedule(
            course_id=course_id,
            teacher_id=teacher_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            classroom=classroom,
        )
        return ServiceResult.ok(data=schedule, trace_id=ctx.trace_id, message="排课创建成功")

    @tool(ToolMeta(
        name="delete_schedule",
        description="删除排课",
        parameters={"schedule_id": {"type": "integer", "description": "排课 ID"}},
        require_permission=True,
    ))
    async def delete_schedule(self, ctx: CTX, schedule_id: int) -> ServiceResult:
        dao: ScheduleDao = get_dao(ctx, self.dao_class)
        if not await dao.schedule_exists(schedule_id):
            return ServiceResult.error(message=f"排课#{schedule_id}不存在", code=404, trace_id=ctx.trace_id)
        await dao.delete_schedule(schedule_id)
        return ServiceResult.ok(data=None, trace_id=ctx.trace_id, message=f"排课#{schedule_id}已删除")

    # ==================== 教师空闲检查 ====================

    @tool(ToolMeta(
        name="check_teacher_availability",
        description="检查某位教师在指定星期几+时间段是否有空。"
                    "会同时查正式排课(schedule)和待审核预排课(pre_schedule PENDING)，"
                    "两者中有任一冲突即返回 available=false。"
                    "家长排课三步：get_child_courses → check_teacher_availability → submit_pre_schedule。",
        parameters={
            "teacher_id":  {"type": "integer", "description": "教师 ID"},
            "day_of_week": {"type": "integer", "description": "星期几：1=周一...7=周日"},
            "start_time":  {"type": "string",  "description": "开始时间（HH:MM）"},
        },
        require_permission=True,
    ))
    async def check_teacher_availability(
        self, ctx: CTX,
        teacher_id: int,
        day_of_week: int,
        start_time: str,
    ) -> ServiceResult:
        """
        检查教师空闲 —— 两张表都要查：
        ① schedule 表：正式排课时间冲突
        ② pre_schedule 表：PENDING 状态的预排课也占时间
        """
        from dal.dao.pre_schedule_dao import PreScheduleDao
        from dal.models.enums import PreScheduleStatus

        check_start = dt_time(*map(int, start_time.split(":")))

        # 查教师姓名
        from dal.dao.user_dao import UserDao
        user_dao = UserDao(ctx.session)
        teacher_user = await user_dao.get_by_id(teacher_id)
        teacher_name = teacher_user.real_name if teacher_user else f"教师#{teacher_id}"

        # ① 查正式排课冲突
        dao: ScheduleDao = get_dao(ctx, self.dao_class)
        has_schedule_conflict = await dao.check_time_conflict(teacher_id, day_of_week, start_time)

        # ② 查预排课 PENDING 冲突
        ps_dao = PreScheduleDao(ctx.session)
        all_pending = await ps_dao.get_pending_reviews()
        has_pre_conflict = False
        for pre in all_pending:
            # 确定预排课关联的教师
            pre_teacher = pre.preferred_teacher_id or (
                pre.course.teacher_id if pre.course else None
            )
            if pre_teacher != teacher_id:
                continue
            # 结构化时间缺失（老数据/没填期望时间）→ 跳过，不误判
            if pre.day_of_week is None or pre.start_time is None or pre.end_time is None:
                continue
            if pre.day_of_week != day_of_week:
                continue
            # 时间重叠判断（结构化字段直接比较，无需再解析文本）
            if not (check_start >= pre.end_time or check_start < pre.start_time):
                has_pre_conflict = True
                break

        has_conflict = has_schedule_conflict or has_pre_conflict

        # 拼冲突详情
        conflict_parts = []
        if has_schedule_conflict:
            conflict_parts.append("正式排课")
        if has_pre_conflict:
            conflict_parts.append("待审核预排课")
        conflict_detail = " + ".join(conflict_parts) if conflict_parts else ""

        return ServiceResult.ok(
            data={
                "teacher_id": teacher_id,
                "teacher_name": teacher_name,
                "day_of_week": day_of_week,
                "start_time": start_time,
                "available": not has_conflict,
                "conflict_type": conflict_detail,
                "message": f"{teacher_name}老师该时段空闲" if not has_conflict
                          else f"{teacher_name}老师该时段已有{conflict_detail}"
            },
            trace_id=ctx.trace_id,
        )


# ── 辅助 ──

def _parse_time(value: str | None) -> dt_time | None:
    if not value:
        return None
    from datetime import datetime
    return datetime.strptime(value, "%H:%M").time()