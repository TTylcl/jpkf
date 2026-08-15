""" dal/dao/user_dao.py 用户数据访问层 —— 纯单表操作 """
from __future__ import annotations

from typing import TYPE_CHECKING

from dal.models.enums import UserType
from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO

if TYPE_CHECKING:
    from dal.models.user_model import User as model


class UserDao(SqlalchemyBaseDAO):
    """
    用户 DAO —— 只做单表操作

    原则：
    - 不写跨表查询（→ QueryService）
    - 不写分页逻辑（→ 基类 paginate()）
    - 不写模糊搜索（→ QueryService）
    - 统一用基类方法处理软删除
    """

    @property
    def model(self):
        from dal.models.user_model import User
        return User

    primary_key = "user_id"
    deleted_field = "deleted_at"

    # ==================== 等值单条查询 ====================

    async def get_by_username(self, username: str) -> model | None:
        return await self.find_one(username=username)

    async def get_by_phone(self, phone: str) -> model | None:
        return await self.find_one(phone=phone)

    async def get_by_email(self, email: str) -> model | None:
        return await self.find_one(email=email)

    # ==================== 等值多条查询 ====================

    async def list_teachers(self, skip: int = 0, limit: int = 100) -> list[model]:
        return await self.find_all(skip=skip, limit=limit, user_type=UserType.TEACHER.value)

    async def list_students(self, skip: int = 0, limit: int = 100) -> list[model]:
        return await self.find_all(skip=skip, limit=limit, user_type=UserType.STUDENT.value)

    # ==================== 存在性检查 ====================

    async def exists_by_username(self, username: str) -> bool:
        return await self.exists(username=username)

    async def exists_by_phone(self, phone: str) -> bool:
        return await self.exists(phone=phone)