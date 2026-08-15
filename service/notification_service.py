"""
service/notification_service.py
通知 Service —— 查询通知、标记已读

【通知类型与推送对象】（定义在 enums.py NotificationType）
① CLASS_REMINDER         — 上课通知（课前 → 老师 + 学生）
② CONSUMPTION_PENDING    — 待消课提醒（课后 → 老师）
③ CONSUMPTION_COMPLETED  — 消课完成通知（消课后 → 家长 + 老师）

【设计说明】
通知由调度器或消课 Service 自动创建，本 Service 只负责查询和已读管理。
前端可通过定时轮询或 SSE 获取新通知。
"""
from __future__ import annotations

from core.context import CTX
from core.service.decorators import tool, ToolMeta
from core.service.utils import get_dao
from core.service.models import ServiceResult
from dal.dao.notification_dao import NotificationDao
from schemas.notification_schema import NotificationItem, NotificationListResponse


class NotificationService:
    resource = "notification"
    dao_class = NotificationDao

    @tool(ToolMeta(
        name="get_my_notifications",
        description="查询当前用户的通知列表。支持只查未读，返回未读计数用于前端红点/角标。",
        parameters={
            "unread_only": {
                "type": "boolean",
                "description": "是否只查未读通知，默认 false（查全部）",
                "default": False,
            },
            "page": {"type": "integer", "default": 1},
            "page_size": {"type": "integer", "default": 20},
        },
        require_permission=True,
    ))
    async def get_my_notifications(
        self, ctx: CTX,
        unread_only: bool = False,
        page: int = 1, page_size: int = 20,
    ) -> ServiceResult:
        """
        查询当前用户的通知

        【使用场景】
        - 家长登录后查看孩子的消课通知
        - 教师查看上课提醒和消课完成通知
        - 学生查看上课提醒
        """
        dao: NotificationDao = get_dao(ctx, self.dao_class)

        if unread_only:
            records = await dao.get_unread_notifications(ctx.user_id)
        else:
            records = await dao.get_notifications(ctx.user_id)

        total = len(records)
        unread_count = await dao.get_unread_count(ctx.user_id)
        start = (page - 1) * page_size
        paged = records[start:start + page_size]
        items = [NotificationItem.model_validate(r) for r in paged]

        return ServiceResult.ok(
            data=NotificationListResponse(
                items=items, total=total, unread_count=unread_count
            ),
            trace_id=ctx.trace_id,
        )

    @tool(ToolMeta(
        name="mark_notification_read",
        description="标记单条通知为已读。用户点击通知后调用。",
        parameters={"notification_id": {"type": "integer", "description": "通知ID"}},
        require_permission=True,
    ))
    async def mark_notification_read(
        self, ctx: CTX, notification_id: int
    ) -> ServiceResult:
        """标记单条通知已读"""
        dao: NotificationDao = get_dao(ctx, self.dao_class)
        notif = await dao.get_by_id(notification_id)
        if not notif:
            return ServiceResult.error(
                message=f"通知#{notification_id}不存在", code=404, trace_id=ctx.trace_id
            )
        if notif.recipient_id != ctx.user_id:
            return ServiceResult.error(
                message="无权操作他人的通知", code=403, trace_id=ctx.trace_id
            )
        await dao.mark_as_read(notification_id)
        return ServiceResult.ok(message="已标记为已读", trace_id=ctx.trace_id)

    @tool(ToolMeta(
        name="mark_all_notifications_read",
        description="一键已读当前用户的所有未读通知。",
        parameters={},
        require_permission=True,
    ))
    async def mark_all_notifications_read(self, ctx: CTX) -> ServiceResult:
        """一键已读全部通知"""
        dao: NotificationDao = get_dao(ctx, self.dao_class)
        count = await dao.mark_all_as_read(ctx.user_id)
        return ServiceResult.ok(
            message=f"已标记 {count} 条通知为已读", trace_id=ctx.trace_id
        )
