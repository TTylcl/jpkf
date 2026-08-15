"""
schemas/notification_schema.py —— 通知 Schema
==============================================
对应 Service：NotificationService
对应数据表：notification

【通知类型】
① CLASS_REMINDER         — 上课通知（课前 → 老师 + 学生）
② CONSUMPTION_PENDING    — 待消课提醒（课后 → 老师）
③ CONSUMPTION_COMPLETED  — 消课完成通知（消课后 → 家长 + 老师）
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    """通知项 —— 推送给用户的消息"""
    id: int = Field(..., description="通知ID")
    recipient_id: int = Field(..., description="接收者用户ID")
    recipient_role: str = Field(..., description="接收者角色")
    notification_type: str = Field(
        ..., description="通知类型：class_reminder / consumption_pending / consumption_completed"
    )
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知正文")
    ref_id: Optional[int] = Field(None, description="关联业务ID")
    ref_type: Optional[str] = Field(None, description="关联业务类型")
    is_read: bool = Field(..., description="是否已读")
    read_at: Optional[datetime] = Field(None, description="阅读时间")
    created_at: Optional[datetime] = Field(None, description="通知创建时间")

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """通知列表响应 —— 含未读计数用于前端红点/角标"""
    items: list[NotificationItem] = Field(..., description="通知列表")
    total: int = Field(..., description="总记录数")
    unread_count: int = Field(0, description="未读通知数")
