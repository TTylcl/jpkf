"""
service/lesson_consumption_service.py
消课 Service —— 教师确认消耗课时，扣减学生剩余课时，通知家长

【业务流程】
1. 上课时间到 → 调度器生成待办 → 教师调用 consume_lesson
2. 验证：排课存在 + 教师身份 + 学生已报名 + 剩余课时 > 0
3. 扣减 StudentCourse.remaining_lessons -= 1
4. 创建 LessonConsumption 记录（保留教师/学生/课程信息，方便统计）
5. 标记对应 TeacherTodo 为已完成
6. 通知家长（发 CONSUMPTION_COMPLETED 通知）
"""
from __future__ import annotations
from datetime import datetime, date

from core.context import CTX
from core.service.decorators import tool, ToolMeta
from core.service.utils import get_dao
from core.service.models import ServiceResult
from core.service.layers import add_service_log
from dal.dao.lesson_consumption_dao import LessonConsumptionDao
from dal.dao.schedule_dao import ScheduleDao
from dal.dao.student_course_dao import StudentCourseDao
from dal.dao.teacher_todo_dao import TeacherTodoDao
from dal.dao.parent_student_dao import ParentStudentDao
from dal.dao.notification_dao import NotificationDao
from dal.models.enums import ConsumptionStatus, NotificationType, TodoStatus
from schemas.lesson_consumption_schema import (
    ConsumeResponse, ConsumptionListItem, ConsumptionListResponse,
)


class LessonConsumptionService:
    resource = "lesson_consumption"
    dao_class = LessonConsumptionDao

    # ==================== 核心：消课 ====================

    @tool(ToolMeta(
        name="consume_lesson",
        description="教师确认消耗一节课时。传入排课ID和学生ID，系统自动扣减学生剩余课时、创建消课记录、标记待办完成、通知家长。",
        parameters={
            "schedule_id": {"type": "integer", "description": "排课ID（哪节排课要消课）"},
            "student_id": {"type": "integer", "description": "要消课的学生ID"},
        },
        require_permission=True,
    ))
    async def consume_lesson(
        self, ctx: CTX, schedule_id: int, student_id: int
    ) -> ConsumeResponse | ServiceResult:
        """
        教师确认消课 —— 消课流程的核心入口

        【安全校验】
        ① 排课必须存在
        ② 只有该排课的任教教师才能消课（schedule.teacher_id == ctx.user_id）
        ③ 同一排课+同一学生不能重复消课
        ④ 学生必须已报名该课程且状态为 active
        ⑤ 学生剩余课时必须 > 0
        """
        # ① 查排课
        schedule_dao = ScheduleDao(ctx.session)
        schedule = await schedule_dao.get_by_id(schedule_id)
        if not schedule:
            return ServiceResult.error(
                message=f"排课#{schedule_id}不存在", code=404, trace_id=ctx.trace_id
            )

        # ② 验证教师身份：只有该课程的任教教师才能消课
        if schedule.teacher_id != ctx.user_id:
            return ServiceResult.error(
                message="只有任教教师才能执行消课操作", code=403, trace_id=ctx.trace_id
            )

        # ③ 防止重复消课（同一排课+同一学生 已确认过就不能再消）
        consumption_dao: LessonConsumptionDao = get_dao(ctx, self.dao_class)
        existing = await consumption_dao.get_consumption_by_schedule_and_student(
            schedule_id, student_id
        )
        if existing:
            return ServiceResult.error(
                message=f"该排课已消过课（记录ID: {existing.id}），请勿重复操作",
                code=409, trace_id=ctx.trace_id,
            )

        # ④ 验证学生已选该课程且有剩余课时
        sc_dao = StudentCourseDao(ctx.session)
        enrollment = await sc_dao.get_by_student_and_course(student_id, schedule.course_id)
        if not enrollment or enrollment.status != "active":
            return ServiceResult.error(
                message=f"该学生未报名此课程或已退课（学生ID:{student_id}）", code=404, trace_id=ctx.trace_id
            )
        if not enrollment.remaining_lessons or enrollment.remaining_lessons <= 0:
            return ServiceResult.error(
                message="该学生剩余课时不足，无法消课", code=409, trace_id=ctx.trace_id
            )

        # ⑤ 扣减课时
        new_remaining = enrollment.remaining_lessons - 1
        lesson_consumed = (enrollment.purchased_lessons or 0) - new_remaining
        await sc_dao.update(enrollment.id, remaining_lessons=new_remaining)

        add_service_log("info",
            f"学生#{student_id} 课程#{schedule.course_id} 课时扣减: "
            f"{enrollment.remaining_lessons} → {new_remaining} (第{lesson_consumed}课时)", ctx)

        # 如果剩余课时归零，标记为已完成
        if new_remaining == 0:
            await sc_dao.update(enrollment.id, status="completed")

        # ⑥ 创建消课记录（核心留痕）
        record = await consumption_dao.create_consumption(
            schedule_id=schedule_id,
            course_id=schedule.course_id,
            teacher_id=ctx.user_id,
            student_id=student_id,
            consumed_at=datetime.now(),
            lesson_index=lesson_consumed,
        )
        add_service_log("info",
            f"消课记录已创建 id={record.id}: 教师#{ctx.user_id} → "
            f"学生#{student_id} 课程#{schedule.course_id} 排课#{schedule_id}", ctx)

        # ⑦ 标记对应待办为已完成
        todo_dao = TeacherTodoDao(ctx.session)
        today = date.today()
        todos = await todo_dao.find_all(
            schedule_id=schedule_id, student_id=student_id,
            todo_date=today, status=TodoStatus.PENDING.value,
        )
        for todo in todos:
            await todo_dao.mark_done(todo.id)
            add_service_log("info", f"待办 id={todo.id} 已自动标记为完成", ctx)

        # ⑧ 通知家长：课时已消耗
        await self._notify_parents(ctx, student_id, schedule.course_id, record.id)

        # ⑨ 通知老师：消课完成
        notif_dao = NotificationDao(ctx.session)
        await notif_dao.create_notification(
            recipient_id=ctx.user_id,
            recipient_role="TEACHER",
            notification_type=NotificationType.CONSUMPTION_COMPLETED.value,
            title="消课完成",
            content=f"您已完成「{schedule.course_name}」的消课，"
                    f"学生「{enrollment.student.real_name if enrollment.student else f'ID:{student_id}'}」"
                    f"剩余课时 {new_remaining}",
            ref_id=record.id,
            ref_type="lesson_consumption",
        )

        # ⑩ 组装响应
        course_name = record.course.course_name if record.course else ""
        student_name = record.student.real_name if record.student else ""
        teacher_name = record.teacher.real_name if record.teacher else ""

        return ConsumeResponse(
            id=record.id,
            schedule_id=schedule_id,
            course_id=schedule.course_id,
            course_name=course_name,
            teacher_id=ctx.user_id,
            teacher_name=teacher_name,
            student_id=student_id,
            student_name=student_name,
            consumed_at=record.consumed_at.isoformat() if record.consumed_at else "",
            remaining_lessons=new_remaining,
            message=f"消课成功！学生 {student_name} 剩余课时: {new_remaining}",
        )

    # ==================== 查询 ====================

    @tool(ToolMeta(
        name="query_consumption_history",
        description="查询消课记录历史。可按教师/学生/课程过滤，用于统计和追溯。",
        parameters={
            "teacher_id": {"type": "integer", "description": "教师ID（可选）", "default": None},
            "student_id": {"type": "integer", "description": "学生ID（可选）", "default": None},
            "course_id": {"type": "integer", "description": "课程ID（可选）", "default": None},
            "page": {"type": "integer", "default": 1},
            "page_size": {"type": "integer", "default": 20},
        },
        require_permission=True,
    ))
    async def query_consumption_history(
        self, ctx: CTX,
        teacher_id: int | None = None,
        student_id: int | None = None,
        course_id: int | None = None,
        page: int = 1, page_size: int = 20,
    ) -> ServiceResult:
        """
        查询消课历史 —— 支持按教师/学生/课程三维度过滤

        【使用场景】
        - 教师：查看自己的消课统计
        - 家长：查看孩子的消课记录
        - 管理员：全局查看
        """
        dao: LessonConsumptionDao = get_dao(ctx, self.dao_class)

        # 按维度查询
        if teacher_id:
            records = await dao.get_consumptions_by_teacher(teacher_id)
        elif student_id:
            records = await dao.get_consumptions_by_student(student_id)
        elif course_id:
            records = await dao.get_consumptions_by_course(course_id)
        else:
            # 无过滤条件返回空（防止全表扫描）
            return ServiceResult.ok(
                data=ConsumptionListResponse(items=[], total=0),
                trace_id=ctx.trace_id,
            )

        # 手动分页
        total = len(records)
        start = (page - 1) * page_size
        paged = records[start:start + page_size]
        items = [ConsumptionListItem.from_orm_model(r) for r in paged]

        return ServiceResult.ok(
            data=ConsumptionListResponse(items=items, total=total),
            trace_id=ctx.trace_id,
        )

    # ==================== 内部方法 ====================

    async def _notify_parents(
        self, ctx: CTX, student_id: int, course_id: int, consumption_id: int
    ) -> None:
        """
        通知学生的所有家长：课时已消耗

        【设计说明】
        放在 try/except 里，通知失败不阻断主流程。
        家长可能不在线，通知存 DB，家长登录后查询即可。
        """
        try:
            parent_dao = ParentStudentDao(ctx.session)
            notif_dao = NotificationDao(ctx.session)

            # 查名称
            from dal.dao.course_dao import CourseDao
            _cd = CourseDao(ctx.session)
            _course = await _cd.get_by_id(course_id)
            _course_name = _course.course_name if _course else f"课程#{course_id}"
            from dal.dao.user_dao import UserDao
            _ud = UserDao(ctx.session)
            _stu = await _ud.get_by_id(student_id)
            _stu_name = _stu.real_name if _stu else f"学生#{student_id}"

            parents = await parent_dao.get_student_parents(student_id)
            if not parents:
                add_service_log("info", f"学生「{_stu_name}」没有绑定家长，跳过通知", ctx)
                return

            for parent in parents:
                await notif_dao.create_notification(
                    recipient_id=parent.parent_id,
                    recipient_role="PARENT",
                    notification_type=NotificationType.CONSUMPTION_COMPLETED.value,
                    title="课时消耗通知",
                    content=f"您的孩子「{_stu_name}」在「{_course_name}」已消耗1课时",
                    ref_id=consumption_id,
                    ref_type="lesson_consumption",
                )
            add_service_log("info",
                f"已通知 {len(parents)} 位家长：学生「{_stu_name}」课程「{_course_name}」课时已消耗", ctx)
        except Exception as e:
            add_service_log("error",
                f"通知家长失败: 学生#{student_id} 课程#{course_id}, error={e}", ctx)
            import traceback
            traceback.print_exc()
