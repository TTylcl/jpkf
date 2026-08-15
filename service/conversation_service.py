"""
service/conversation_service.py —— 会话生命周期管理，内部基础设施，不对 LLM 暴露
负责「会话创建/查找 + 消息存取 + 历史加载」
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from dal.dao.session_info_dao import SessionInfoDao
from dal.dao.chat_message_dao import ChatMessageDao
from dal.models.enums import SenderType

class ConversationService:
    """
    会话管理 + 消息持久化。

    这是内部基础设施，**不加 @tool 装饰器**，LLM 不可直接调用。
    消息存取在 api router 层完成。
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_info_dao = SessionInfoDao(session)
        self.chat_message_dao = ChatMessageDao(session)

    #会话管理-----------------
    async def get_or_create_session(self, user_id:int,thread_id:str|None=None):
        """
        获取或创建会话。

        - 传了 thread_id → 查已有会话，找不到则用这个 thread_id 新建
        - 没传 thread_id → 生成新 UUID 并创建会话
        """    
        if thread_id:  # 传了 thread_id
            existing = await self.session_info_dao.get_by_thread_id(thread_id)
            if existing:  # 已有会话
                return existing
        new_thread_id = thread_id or str(uuid.uuid4())
        return await self.session_info_dao.create(
            user_id=user_id,
            thread_id=new_thread_id,
            status="active",
            start_time=datetime.now(),
        )
    async def close_session(self, session_id: int):
        """关闭会话"""
        return await self.session_info_dao.close_session(session_id)

    # 消息存取-----------------
    async def save_message(
        self, session_id: int, sender_type: SenderType, content: str,
        sender_id: int | None = None, intent: str | None = None,
        is_auto_reply: int = 0,
    ):
        """保存消息到会话表中"""
        return await self.chat_message_dao.create(
            session_id=session_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            intent=intent,
            is_auto_reply=is_auto_reply,
        )

    #快捷：保存用户消息
    async def save_user_message(self, session_id: int, content: str, user_id: int):
        """快捷：保存用户消息"""
        return await self.save_message(
            session_id=session_id,
            sender_type=SenderType.USER,
            content=content,
            sender_id=user_id,
        )
    async def save_ai_message(
        self, session_id: int, content: str, intent: str | None = None
    ):
        """快捷：保存 AI 回复"""
        return await self.save_message(
            session_id=session_id,
            sender_type=SenderType.ROBOT,
            content=content,
            intent=intent,
            is_auto_reply=1,
        )

    #加载历史消息-----------------
    async def get_history_messages(self, session_id: int, limit: int = 20) -> List[BaseMessage]:
        """从 DB 加载历史消息，转为 LangChain BaseMessage 列表。

        用于注入 graph state，让 LLM 感知上下文。"""
        records = await self.chat_message_dao.get_recent_message(session_id, limit)
       
        messages: List[BaseMessage] = []
        for record in records:
            if record.sender_type == SenderType.USER:
                messages.append(HumanMessage(content=record.content))
            else:
                messages.append(AIMessage(content=record.content))
        return messages



