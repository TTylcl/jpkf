"""
service/teacher_todo_service.py
教师待办 Service —— 查看今日待办、手动标记完成

【业务流程】
调度器自动生成 → 教师打开系统看今日待办 → 消课后待办自动完成
也支持教师手动标记完成（不依赖消课流程）
"""
from __future__ import annotations

from core.context import CTX
from core.service.decorators import tool, ToolMeta
from core.service.utils import get_dao
from core.service.models import ServiceResult
from dal.dao.teacher_todo_dao import TeacherTodoDao
from dal.dao.pre_schedule_dao import PreScheduleDao
from dal.dao.notification_dao import NotificationDao
from dal.models.enums import PreScheduleStatus, NotificationType
from schemas.teacher_todo_schema import TodoItem, TodoListResponse


class TeacherTodoService:
    resource = "teacher_todo"
    dao_class = TeacherTodoDao

    @tool(ToolMeta(
        name="get_my_todos",
        description="查询教师自己的待办列表（含消课待办 + 待审核预排课）。默认查今天。登录后应主动调用。",
        parameters={
            "todo_date": {
                "type": "string",
                "description": "日期（YYYY-MM-DD 格式），不传默认今天",
                "default": None,
            },
            "page": {"type": "integer", "default": 1},
            "page_size": {"type": "integer", "default": 50},
        },
        require_permission=True,
    ))
    async def get_my_todos(
        self, ctx: CTX,
        todo_date: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> ServiceResult:
        """
        教师查看待办 —— 包含消课待办 + 待审核预排课

        【返回格式】
        TodoListResponse: items 是待办列表，total 是总数
        每项含 todo_type 区分类型：consumption=消课 / pre_schedule_review=预排课审核
        """
        dao: TeacherTodoDao = get_dao(ctx, self.dao_class)

        if todo_date:
            from datetime import datetime
            target_date = datetime.strptime(todo_date, "%Y-%m-%d").date()
        else:
            from datetime import date
            target_date = date.today()

        items: list[TodoItem] = []

        # ── ① 消课待办 ──
        records = await dao.get_todos_by_date(ctx.user_id, target_date)
        for r in records:
            items.append(TodoItem(
                id=r.id,
                teacher_id=r.teacher_id,
                schedule_id=r.schedule_id,
                course_id=r.course_id,
                student_id=r.student_id,
                student_name=r.student.real_name if r.student else f"学生{r.student_id}",
                todo_date=r.todo_date,
                title=r.title,
                detail=r.detail,
                status=r.status,
                todo_type="consumption",
            ))

        # ── ② 待审核预排课（与当前教师相关） ──
        ps_dao = PreScheduleDao(ctx.session)
        all_pending = await ps_dao.get_pending_reviews()
        for pre in all_pending:
            # 筛选：预排课指定教师匹配，或课程默认教师匹配
            related_teacher_id = pre.preferred_teacher_id or (
                pre.course.teacher_id if pre.course else None
            )
            if related_teacher_id != ctx.user_id:
                continue

            student_name = pre.student.real_name if pre.student else f"学生{pre.student_id}"
            course_name = pre.course.course_name if pre.course else f"课程{pre.course_id}"
            preferred = (
                f"期望时间: {pre.preferred_time}" if pre.preferred_time
                else "未指定时间"
            )

            items.append(TodoItem(
                id=pre.id,
                teacher_id=related_teacher_id,
                schedule_id=0,
                course_id=pre.course_id,
                student_id=pre.student_id,
                student_name=student_name,
                todo_date=target_date,
                title=f"待审核预排课：{student_name} - {course_name}",
                detail=f"{preferred}。提交的预排课申请等待审核",
                status="pending",
                todo_type="pre_schedule_review",
            ))

        # ── ③ 上课提醒通知 ──
        notif_dao = NotificationDao(ctx.session)
        notifs = await notif_dao.get_unread_notifications(ctx.user_id, limit=50)
        for n in notifs:
            if n.notification_type not in (
                NotificationType.CLASS_REMINDER.value,
                NotificationType.CLASS_REMINDER_HOUR_BEFORE.value,
                NotificationType.CLASS_REMINDER_DAY_BEFORE.value,
                NotificationType.CONSUMPTION_PENDING.value,
            ):
                continue
            items.append(TodoItem(
                id=n.id,
                teacher_id=ctx.user_id,
                schedule_id=n.ref_id if n.ref_type == "schedule" else 0,
                course_id=0,
                student_id=0,
                student_name="",
                todo_date=target_date,
                title=n.title,
                detail=n.content,
                status="unread",
                todo_type="class_reminder",
            ))

        # 分页
        total = len(items)
        start = (page - 1) * page_size
        paged = items[start:start + page_size]

        return ServiceResult.ok(
            data=TodoListResponse(items=paged, total=total),
            trace_id=ctx.trace_id,
        )

    @tool(ToolMeta(
        name="mark_todo_done",
        description="手动标记一条待办为已完成。消课流程中会自动标记，此工具用于手动补标。",
        parameters={"todo_id": {"type": "integer", "description": "待办ID"}},
        require_permission=True,
    ))
    async def mark_todo_done(self, ctx: CTX, todo_id: int) -> ServiceResult:
        """手动标记待办完成"""
        dao: TeacherTodoDao = get_dao(ctx, self.dao_class)
        todo = await dao.get_by_id(todo_id)
        if not todo:
            return ServiceResult.error(
                message=f"待办#{todo_id}不存在", code=404, trace_id=ctx.trace_id
            )
        if todo.teacher_id != ctx.user_id:
            return ServiceResult.error(
                message="无权操作他人的待办", code=403, trace_id=ctx.trace_id
            )
        updated = await dao.mark_done(todo_id)
        return ServiceResult.ok(
            data=TodoItem.model_validate(updated),
            message="待办已标记完成",
            trace_id=ctx.trace_id,
        )
