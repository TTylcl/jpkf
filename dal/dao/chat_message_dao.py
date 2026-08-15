"""dal/dao/chat_message_dao.py —— 聊天消息 DAO"""

from __future__ import annotations
from typing import TYPE_CHECKING
from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO
from sqlalchemy import select 
from sqlalchemy.orm import joinedload 

if TYPE_CHECKING:
    from dal.models.chat_message_model import ChatMessage as Model

class ChatMessageDao(SqlalchemyBaseDAO):
    @property
    def model(self):
        from dal.models.chat_message_model import ChatMessage
        return ChatMessage
    primary_key = "msg_id"  # 主键
    deleted_field = None  # 软删除字段不使用，可忽略
    async def list_by_session_id(self, session_id: int, skip: int = 0, limit: int = 20) -> list[Model]:
        """根据会话id查消息，按时间创建升序排序"""
        stmt= (
            select(self.model)
            .where(self.model.session_id == session_id)
            .order_by(self.model.created_at.asc())
            .offset(skip)
            .limit(limit)
        
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_message(self, session_id: int,limit:int = 20) -> list[Model]:
        """获取回合最近N条消息，注入graph上下文"""
        stmt= (
            select(self.model)
            .where(self.model.session_id == session_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        records.reverse()  # 倒序排列，返回正序
        return records  #








