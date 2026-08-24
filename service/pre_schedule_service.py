"""
service/pre_schedule_service.py
预排课 Service —— 家长提交 → 老师审核 → 生成正式排课
"""
from __future__ import annotations

from core.context import CTX
from core.service.decorators import tool, ToolMeta
from core.service.utils import get_dao, parse_preferred_time
from core.service.models import ServiceResult
from dal.dao.pre_schedule_dao import PreScheduleDao
from dal.dao.parent_student_dao import ParentStudentDao
from dal.dao.course_dao import CourseDao

from dal.models.enums import PreScheduleStatus
from schemas.pre_schedule_schema import (
    PreScheduleResponse,
    PreScheduleListResponse,
    SubmitResponse,
    ReviewResponse,
)


class PreScheduleService:
    resource = "pre_schedule"
    dao_class = PreScheduleDao

    # ==================== 家长提交 ====================

    @tool(ToolMeta(
        name="submit_pre_schedule",
        description="家长为孩子提交预排课申请。需要先绑定家长-学生关系。",
        parameters={
            "parent_id": {"type": "integer", "description": "家长用户ID"},
            "student_id": {"type": "integer", "description": "孩子（学生）ID"},
            "course_id": {"type": "integer", "description": "课程ID"},
            "preferred_time": {"type": "string", "description": "期望上课时间（如：周一 09:00-10:30）", "default": None},
            "preferred_teacher_id": {"type": "integer", "description": "期望教师ID（可选）", "default": None},
        },
        require_permission=True,
        owner_param="parent_id",
        owner_roles=("parent",),
    ))
    async def submit_pre_schedule(
        self,
        ctx: CTX,
        parent_id: int,
        student_id: int,
        course_id: int,
        preferred_time: str | None = None,
        preferred_teacher_id: int | None = None,
    ) -> SubmitResponse | ServiceResult:
        """家长提交预排课申请"""
        # ① 验证绑定关系
        bind_dao = ParentStudentDao(ctx.session)
        bindings = await bind_dao.get_parent_students(parent_id)
        if not any(b.student_id == student_id for b in bindings):
            return ServiceResult.error(
                message=f"家长与孩子无绑定关系（家长ID:{parent_id}，学生ID:{student_id}），请先绑定",
                code=403,
                trace_id=ctx.trace_id,
            )
        # ② 验证课程是否报名 + 剩余课时 > 0
        from dal.dao.student_course_dao import StudentCourseDao
        sc_dao = StudentCourseDao(ctx.session)
        et = await sc_dao.get_by_student_and_course(student_id, course_id)
        if not et or et.status != 'active':
            return ServiceResult.error(
                message=(
                    f"学生「{et.student.real_name if et and et.student else f'ID:{student_id}'}」"
                    f"未报名课程「{et.course.course_name if et and et.course else f'ID:{course_id}'}」，"
                    f"无法安排正课。请先引导学生申请体验课（试听课），体验后再正式报名。"),
                code=403,
                trace_id=ctx.trace_id,
            )
        if not et.remaining_lessons or et.remaining_lessons <= 0:
            return ServiceResult.error(
                message=(
                    f"学生「{et.student.real_name if et.student else f'ID:{student_id}'}」"
                    f"在课程「{et.course.course_name if et.course else f'ID:{course_id}'}」的剩余课时为 "
                    f"{et.remaining_lessons or 0}，课时不足无法排课。"
                    f"请联系教务续费或购买课时。"),
                code=409,
                trace_id=ctx.trace_id,
            )
        # ③ 解析 preferred_time → 结构化字段（解析失败当场拒绝，避免冲突检查静默漏检）
        day_of_week = start_time = end_time = None
        if preferred_time:
            parsed = parse_preferred_time(preferred_time)
            if parsed is None:
                return ServiceResult.error(
                    message=f"无法解析期望时间「{preferred_time}」，请使用「周X HH:MM-HH:MM」格式（如：周一 09:00-10:30）",
                    code=400,
                    trace_id=ctx.trace_id,
                )
            day_of_week = parsed["day_of_week"]
            start_time = parsed["start_time"]
            end_time = parsed["end_time"]

        # ④ 创建预排课
        dao: PreScheduleDao = get_dao(ctx, self.dao_class)
        record = await dao.submit(
            student_id=student_id,
            course_id=course_id,
            preferred_time=preferred_time,
            preferred_teacher_id=preferred_teacher_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
        )

        return SubmitResponse(
            id=record.id,
            student_id=record.student_id,
            student_name=record.student.real_name if record.student else "",
            course_id=record.course_id,
            course_name=record.course.course_name if record.course else "",
            status=record.status.value,
            message="提交成功，等待老师审核",
        )

    # ==================== 老师审核 ====================

    @tool(ToolMeta(
        name="review_pre_schedule",
        description="老师审核预排课。通过后生成正式排课，拒绝则填写备注。",
        parameters={
            "pre_schedule_id": {"type": "integer", "description": "预排课ID"},
            "action": {"type": "string", "description": "审核动作：approve=通过, reject=拒绝"},
            "day_of_week": {"type": "integer", "description": "排课星期几：1=周一...7=周日（通过时必填）", "default": 0},
            "start_time": {"type": "string", "description": "上课开始时间 HH:MM（通过时必填）", "default": ""},
            "end_time": {"type": "string", "description": "上课结束时间 HH:MM（通过时必填）", "default": ""},
            "classroom": {"type": "string", "description": "教室（可选）", "default": None},
            "review_note": {"type": "string", "description": "审核备注（拒绝时建议填写原因）", "default": None},
        },
        require_permission=True,
    ))
    async def review_pre_schedule(
        self,
        ctx: CTX,
        pre_schedule_id: int,
        action: str,
        day_of_week: int = 0,
        start_time: str = "",
        end_time: str = "",
        classroom: str | None = None,
        review_note: str | None = None,
    ) -> ReviewResponse | ServiceResult:
        """老师审核预排课"""
        dao: PreScheduleDao = get_dao(ctx, self.dao_class)

        # ① 查预排课是否存在
        pre = await dao.get_by_id_with_details(pre_schedule_id)
        if not pre:
            return ServiceResult.error(
                message=f"预排课#{pre_schedule_id}不存在或已处理",
                code=404,
                trace_id=ctx.trace_id,
            )

        if pre.status != PreScheduleStatus.PENDING:
            return ServiceResult.error(
                message=f"该预排课已审核，当前状态: {pre.status.value}",
                code=409,
                trace_id=ctx.trace_id,
            )

        # ② 拒绝：更新状态 + 备注
        if action == "reject":
            await dao.review(
                pre_schedule_id=pre_schedule_id,
                reviewer_id=ctx.user_id,
                status=PreScheduleStatus.REJECTED,
                review_note=review_note,
            )
            return ReviewResponse(
                pre_schedule_id=pre_schedule_id,
                student_name=pre.student.real_name if pre.student else "",
                course_name=pre.course.course_name if pre.course else "",
                teacher_name=pre.preferred_teacher.real_name if pre.preferred_teacher else (
                    pre.course.teacher_name if pre.course else ""
                ),
                status=PreScheduleStatus.REJECTED.value,
                message=f"已拒绝: {review_note or '无备注'}",
            )

        # ③ 通过：校验排课参数
        if action != "approve":
            return ServiceResult.error(
                message=f"无效的审核动作: {action}，只支持 approve / reject",
                code=400,
                trace_id=ctx.trace_id,
            )

        if not day_of_week or not start_time or not end_time:
            return ServiceResult.error(
                message="审核通过必须提供 day_of_week、start_time、end_time",
                code=400,
                trace_id=ctx.trace_id,
            )

        # ④ 确定教师
        teacher_id = pre.preferred_teacher_id or pre.course.teacher_id

        # ⑤ 生成正式排课 —— 走 ScheduleService.create_schedule 完整校验链
        #   （校验：课程存在 / 教师匹配 / 学生已报名且有剩余课时 / 时间冲突）
        #   时间冲突校验已统一由 create_schedule 负责，此处不再重复
        from service.schedule_service import ScheduleService
        schedule_svc = ScheduleService()
        schedule_result = await schedule_svc.create_schedule(
            ctx=ctx,
            course_id=pre.course_id,
            teacher_id=teacher_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            classroom=classroom,
            _exclude_pre_schedule_id=pre_schedule_id,  # 排除自身，避免自己跟自己冲突
        )
        if not schedule_result.success:
            return schedule_result  # 校验失败直接透传错误

        schedule = schedule_result.data

        # ⑥ 将提交预排课的学生加入排课学生表
        from dal.dao.student_schedule_dao import StudentScheduleDao
        ss_dao = StudentScheduleDao(ctx.session)
        await ss_dao.create(
            student_id=pre.student_id,
            schedule_id=schedule.id,
        )

        # ⑦ 审核通过后自动给学生报名（如果未选），并从课程复制课时数据
        from dal.dao.student_course_dao import StudentCourseDao
        course_dao = CourseDao(ctx.session)
        course = await course_dao.get_by_id(pre.course_id)
        total = course.total_lessons if course else 0

        sc_dao = StudentCourseDao(ctx.session)
        existing = await sc_dao.get_by_student_and_course(pre.student_id, pre.course_id)
        if not existing:
            await sc_dao.create(
                student_id=pre.student_id,
                course_id=pre.course_id,
                status="active",
                purchased_lessons=total,
                remaining_lessons=total,
            )
        elif existing.status == 'dropped':
            await sc_dao.update(existing.id, status="active",
                                purchased_lessons=total,
                                remaining_lessons=total)

        # ⑧ 更新预排课状态为通过
        await dao.review(
            pre_schedule_id=pre_schedule_id,
            reviewer_id=ctx.user_id,
            status=PreScheduleStatus.APPROVED,
            review_note=review_note,
        )

        return ReviewResponse(
            pre_schedule_id=pre_schedule_id,
            student_name=pre.student.real_name if pre.student else "",
            course_name=pre.course.course_name if pre.course else "",
            teacher_name=pre.preferred_teacher.real_name if pre.preferred_teacher else (
                pre.course.teacher_name if pre.course else ""
            ),
            status=PreScheduleStatus.APPROVED.value,
            schedule_id=schedule.id,
            message="审核通过，正式排课已生成",
        )

    # ==================== 查询 ====================

    @tool(ToolMeta(
        name="get_pending_reviews",
        description="查询所有待审核的预排课（老师用）",
        parameters={
            "page": {"type": "integer", "default": 1},
            "page_size": {"type": "integer", "default": 20},
        },
        require_permission=True,
    ))
    async def get_pending_reviews(
        self, ctx: CTX, page: int = 1, page_size: int = 20
    ) -> ServiceResult:
        """老师查看待审核列表"""
        dao: PreScheduleDao = get_dao(ctx, self.dao_class)
        skip = (page - 1) * page_size
        records = await dao.get_pending_reviews(skip=skip, limit=page_size)
        total = await dao.count(status=PreScheduleStatus.PENDING)

        items = [PreScheduleResponse.from_orm_model(r) for r in records]
        return ServiceResult.ok(
            data=PreScheduleListResponse(items=items, total=total),
            trace_id=ctx.trace_id,
        )

    @tool(ToolMeta(
        name="get_my_submissions",
        description="查询家长为孩子提交的预排课记录",
        parameters={
            "parent_id": {"type": "integer", "description": "家长用户ID"},
            "page": {"type": "integer", "default": 1},
            "page_size": {"type": "integer", "default": 20},
        },
        require_permission=True,
        owner_param="parent_id",
        owner_roles=("parent",),
    ))
    async def get_my_submissions(
        self, ctx: CTX, parent_id: int, page: int = 1, page_size: int = 20
    ) -> ServiceResult:
        """家长查看自己孩子的预排课提交记录"""
        # ① 先查出所有孩子
        bind_dao = ParentStudentDao(ctx.session)
        bindings = await bind_dao.get_parent_students(parent_id)
        if not bindings:
            return ServiceResult.ok(
                data=PreScheduleListResponse(items=[], total=0),
                trace_id=ctx.trace_id,
            )

        # ② 查每个孩子的预排课
        dao: PreScheduleDao = get_dao(ctx, self.dao_class)
        all_items: list[PreScheduleResponse] = []
        for b in bindings:
            records = await dao.get_by_student(b.student_id)
            all_items.extend(PreScheduleResponse.from_orm_model(r) for r in records)

        # ③ 分页
        total = len(all_items)
        start = (page - 1) * page_size
        paged = all_items[start:start + page_size]

        return ServiceResult.ok(
            data=PreScheduleListResponse(items=paged, total=total),
            trace_id=ctx.trace_id,
        )
