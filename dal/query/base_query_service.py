"""
dal/query/base_query_service.py
QueryService 基类 —— 提供分页、排序等通用能力
"""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from typing import Any

from dal.query import PageResult


class BaseQueryService:
    """所有 QueryService 的基类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _paginate(
        self,
        stmt: Select,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResult:
        """通用分页：传入 select，返回 PageResult"""
        # count 不需要排序
        count_stmt = select(func.count()).select_from(
            stmt.order_by(None).subquery()
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return PageResult(items=items, total=total, page=page, page_size=page_size)

    @staticmethod
    def _apply_ordering(stmt: Select, model: type, order_by: str | None, default_field: str = "created_at") -> Select:
        """通用排序"""
        if not order_by:
            default_col = getattr(model, default_field, None)
            return stmt.order_by(default_col.desc()) if default_col else stmt

        descending = order_by.startswith("-")
        field_name = order_by[1:] if descending else order_by
        column = getattr(model, field_name, None)

        if column is None:
            default_col = getattr(model, default_field, None)
            return stmt.order_by(default_col.desc()) if default_col else stmt

        return stmt.order_by(column.desc() if descending else column.asc())