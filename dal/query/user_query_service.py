"""
dal/query/user_query_service.py
用户查询服务 —— Agent 驱动的灵活查询

与 course_query_service.py 完全同款设计：
- 一个 query_users 方法承接所有用户查询
- UserFilters 约束 Agent 输入白名单
- 统一返回 PageResult
- 分页、排序由 BaseQueryService 基类提供
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from dal.models.user_model import User
from dal.models.enums import UserType
from dal.query.base_query_service import BaseQueryService
from dal.query import PageResult


# ============================================================
# 过滤器模型 —— Agent 可自省的白名单
# ============================================================

@dataclass
class UserFilters:
    """
    用户查询过滤器

    Agent 可以任意组合这些字段，但不能超出这个白名单。
    所有字段都是可选的，不传则不过滤。
    """
    keyword: str | None = None           # 模糊搜索（姓名 / 用户名 / 手机号）
    user_type: UserType | None = None    # 教师 / 学生 / 家长
    created_after: datetime | None = None
    created_before: datetime | None = None


# ============================================================
# QueryService
# ============================================================

class UserQueryService(BaseQueryService):
    """用户查询服务 —— 一个方法承接所有查询"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    # ── 统一查询入口 ──

    async def query_users(
        self,
        filters: UserFilters | None = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str | None = None,
    ) -> PageResult:
        """Agent 调用用户查询的唯一入口"""
        filters = filters or UserFilters()
        stmt = self._build_query(filters)
        stmt = self._apply_ordering(stmt, User, order_by)
        return await self._paginate(stmt, page, page_size)

    # ── SQL 构建 ──

    def _build_query(self, f: UserFilters) -> Select:
        """根据过滤器构建 SELECT 语句"""
        stmt = select(User).where(User.deleted_at.is_(None))

        if f.keyword:
            stmt = stmt.where(
                or_(
                    User.real_name.ilike(f"%{f.keyword}%"),
                    User.username.ilike(f"%{f.keyword}%"),
                    User.phone.ilike(f"%{f.keyword}%"),
                )
            )

        if f.user_type is not None:
            stmt = stmt.where(User.user_type == f.user_type.value)

        if f.created_after is not None:
            stmt = stmt.where(User.created_at >= f.created_after)

        if f.created_before is not None:
            stmt = stmt.where(User.created_at <= f.created_before)

        return stmt

    # ── 统计查询 ──

    async def count_by_type(self, user_type: UserType) -> int:
        """按用户类型统计数量（聚合查询，不走分页）"""
        stmt = select(func.count()).select_from(User).where(
            User.user_type == user_type.value,
            User.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0