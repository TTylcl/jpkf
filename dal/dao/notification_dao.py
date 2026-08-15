"""
dal/dao/notification_dao.py
通知 DAO —— 上课通知 / 待消课提醒 / 消课完成通知的存储与查询

【通知类型与推送对象】
① CLASS_REMINDER         — 课前 → 老师 + 学生
② CONSUMPTION_PENDING    — 课后 → 老师（提醒确认消课）
③ CONSUMPTION_COMPLETED  — 消课后 → 家长 + 老师
"""
from __future__ import annotations
from datetime import datetime
from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO
from dal.models.notification_model import Notification


class NotificationDao(SqlalchemyBaseDAO):
    """通知 DAO"""
    primary_key = "id"
    deleted_field = "deleted_at"

    @property
    def model(self):
        return Notification

    async def create_notification(
        self,
        recipient_id: int,
        recipient_role: str,
        notification_type: str,
        title: str,
        content: str,
        ref_id: int | None = None,
        ref_type: str | None = None,
    ) -> Notification:
        """创建通知——调度器或 Service 在关键节点调用"""
        return await self.create(
            recipient_id=recipient_id,
            recipient_role=recipient_role,
            notification_type=notification_type,
            title=title,
            content=content,
            ref_id=ref_id,
            ref_type=ref_type,
            is_read=False,
        )

    async def get_unread_notifications(
        self, recipient_id: int, limit: int = 50
    ) -> list[Notification]:
        """查某用户的所有未读通知"""
        return await self.find_all(
            recipient_id=recipient_id, is_read=False, limit=limit
        )

    async def get_notifications(
        self, recipient_id: int, skip: int = 0, limit: int = 50
    ) -> list[Notification]:
        """查某用户的所有通知（含已读/未读）"""
        return await self.find_all(recipient_id=recipient_id, skip=skip, limit=limit)

    async def mark_as_read(self, notification_id: int) -> Notification | None:
        """标记单条通知为已读"""
        return await self.update(
            notification_id, is_read=True, read_at=datetime.now()
        )

    async def mark_all_as_read(self, recipient_id: int) -> int:
        """批量标记某用户所有未读通知为已读，返回更新数量"""
        unread = await self.find_all(recipient_id=recipient_id, is_read=False)
        for n in unread:
            await self.update(n.id, is_read=True, read_at=datetime.now())
        return len(unread)

    async def get_unread_count(self, recipient_id: int) -> int:
        """获取某用户未读通知数量——前端红点/角标用"""
        return await self.count(recipient_id=recipient_id, is_read=False)

    async def notification_exists(
        self, recipient_id: int, notification_type: str, ref_id: int
    ) -> bool:
        """检查某用户是否已收到过某排课的同类通知（防重复推送）"""
        return await self.exists(
            recipient_id=recipient_id,
            notification_type=notification_type,
            ref_id=ref_id,
        )