"""
dal/models/notification_model.py
通知表 —— 覆盖上课前/课后待消课/消课完成全流程推送

【设计目的】
✅ 上课前：推送上课提醒给老师和学生
✅ 下课后：推送待消课提醒给老师（提醒确认消课）
✅ 消课后：推送消课完成通知给家长和老师（双方知晓课时已消耗）

【通知类型】（定义在 dal/models/enums.py NotificationType）
① CLASS_REMINDER         — 上课通知（课前 → 老师 + 学生）
② CONSUMPTION_PENDING    — 待消课提醒（课后 → 老师，提醒确认消课）
③ CONSUMPTION_COMPLETED  — 消课完成通知（消课后 → 家长 + 老师）

【字段说明】
- recipient_id: 接收者，可以是老师/学生/家长
- ref_id: 关联业务ID（如 consumption_id / schedule_id），方便追溯
- is_read + read_at: 已读状态，用于前端红点提示
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Boolean, Text, Index, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from dal.models.base_model import Base

class Notification(Base):
    __tablename__ = "notification"

    __table_args__ = (
        Index("idx_notif_recipient_read", "recipient_id", "is_read"),  # 查某用户未读通知
        Index("idx_notif_created_at", "created_at"),                    # 按时间排序
        Index("idx_notif_type", "notification_type"),                   # 按类型筛选
        {"comment": "通知表 —— 上课通知 / 待消课提醒 / 消课完成通知"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="通知ID")
    recipient_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="接收者用户ID（老师/学生/家长）"
    )
    recipient_role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="接收者角色：TEACHER / STUDENT / PARENT"
    )
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="通知类型：class_reminder / consumption_pending / consumption_completed"
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="通知标题，如：上课提醒 / 待消课提醒 / 课时消耗通知"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="通知正文，如：您有一节钢琴课将在10:00开始"
    )
    ref_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="关联业务ID（schedule_id 或 consumption_id）"
    )
    ref_type: Mapped[Optional[str]] = mapped_column(
        String(50), comment="关联业务类型：schedule / lesson_consumption"
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否已读（前端红点提示用）"
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True, comment="阅读时间（点击查看即标记）"
    )

    # Base 继承的时间字段覆盖
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, index=True, nullable=True, comment="删除时间"
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, to={self.recipient_id}({self.recipient_role}), type={self.notification_type}, read={self.is_read})>"