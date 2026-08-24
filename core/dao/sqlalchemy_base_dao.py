from __future__ import annotations
""" core/dao/sqlalchemy_base_dao.py 有状态DAO基类 - FastAPI依赖注入专用 """
from typing import Any, Type, TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select, Select, func

from sqlalchemy.orm import DeclarativeBase

T = TypeVar("T", bound=DeclarativeBase)


class SqlalchemyBaseDAO(Generic[T]):
    model: Type[T]
    primary_key: str = "id"
    deleted_field: str | None = "deleted_at"

    def __init__(self, session: AsyncSession):
        self.session = session

    def _apply_deleted_filter(self, stmt: Select, include_deleted: bool) -> Select:
        """统一软删除过滤 - 所有select查询自动调用"""
        if not include_deleted and self.deleted_field is not None:
            deleted_field = getattr(self.model, self.deleted_field)
            stmt = stmt.where(deleted_field.is_(None))
        return stmt

    # ==================== 封装便捷查询方法（对应你要的find系列） ====================
    async def find_one(
        self,
        include_deleted: bool = False,
        **conditions: Any
    ) -> T | None:
        """等值条件查询单条记录，自动处理软删除"""
        stmt = select(self.model).filter_by(**conditions)
        stmt = self._apply_deleted_filter(stmt, include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        **conditions: Any
    ) -> list[T]:
        """等值条件查询多条记录，支持分页，自动处理软删除"""
        stmt = select(self.model).filter_by(**conditions)
        stmt = self._apply_deleted_filter(stmt, include_deleted)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 核心基础方法 ====================
    async def get_by_id(
        self,
        record_id: Any,
        include_deleted: bool = False
    ) -> T | None:
        """主键查询 - 走一级缓存，性能最优"""
        instance = await self.session.get(self.model, record_id)
        if not instance:
            return None
        # 只有没要求包含已删除，且有删除字段，且字段有值时，才返回None
        if not include_deleted and self.deleted_field:
            deleted_value = getattr(instance, self.deleted_field)
            if deleted_value is not None:
                return None
        return instance

    async def count(
        self,
        include_deleted: bool = False,
        **conditions: Any
    ) -> int:
        """统计数量，无字段歧义错误"""
        stmt = select(func.count(getattr(self.model, self.primary_key))).filter_by(**conditions)
        stmt = self._apply_deleted_filter(stmt, include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(
        self,
        include_deleted: bool = False,
        **conditions: Any
    ) -> bool:
        """检查是否存在，性能最优"""
        stmt = select(self.model).filter_by(**conditions).limit(1)
        stmt = self._apply_deleted_filter(stmt, include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create(self, **data: Any) -> T:
        """新增记录"""
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, record_id: Any, **data: Any) -> T | None:
        """按主键更新"""
        instance = await self.get_by_id(record_id)
        if instance:
            for key, value in data.items():
                setattr(instance, key, value)
            await self.session.flush()
            await self.session.refresh(instance)
        return instance

    async def soft_delete(self, record_id: Any) -> bool:
        """软删除"""
        instance = await self.get_by_id(record_id, include_deleted=True)
        if not instance:
            return False
        if self.deleted_field:
            setattr(instance, self.deleted_field, datetime.now())
            await self.session.flush()
        return True
    async def paginate(
        self,
        stmt: Select,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Any], int]:
        """
        通用分页，接收任意 select 语句，返回 (数据列表, 总数)

        用法：
            stmt = select(User).where(User.user_type == "teacher")
            items, total = await dao.paginate(stmt, page=1, page_size=20)
        """
        # 自动应用软删除过滤（如果模型有 deleted_field）
        stmt = self._apply_deleted_filter(stmt, include_deleted=False)

        # count 子查询
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total    