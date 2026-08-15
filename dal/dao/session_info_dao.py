""" dal/dao/session_info_dao.py 会话信息DAO - 2026标准架构 """

from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime
from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO
if TYPE_CHECKING:
    from dal.models.session_info_model import SessionInfo as Model

class SessionInfoDao(SqlalchemyBaseDAO):
    @property # 延迟导入，彻底解决循环依赖
    def model(self) : 
        from dal.models.session_info_model import SessionInfo
        return SessionInfo
    primary_key = "session_id"  # 主键
    deleted_field = None  # 软删除字段不使用，可忽略
    # 根据thread_id获取会话信息
    async def get_by_thread_id(self, thread_id: str) -> Model | None:
        return await self.find_one(thread_id=thread_id)
    # 根据用户id获取会话列表
    async def list_by_user_id(self, user_id: int, skip: int = 0, limit: int = 20) -> list[Model]:
        return await self.find_all(user_id=user_id, skip=skip, limit=limit)
    # 关闭会话
    async def close_session(self, session_id: int) -> Model | None:
        return await self.update(session_id, status="closed", end_time=datetime.now())















