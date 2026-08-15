"""
dal/query/course_query_service.py
课程查询服务 —— Agent 驱动的灵活查询

原则：
- 一个 query_courses 方法承接所有课程查询
- 过滤条件通过 Pydantic 模型约束，Agent 可自省
- 统一返回 PageResult
- 软删除、分页由基类统一处理
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from dal.models.course_model import Course
from dal.models.enums import CourseType, CourseStatus
from dal.query.base_query_service import BaseQueryService, PageResult



# ============================================================
# 过滤器模型 —— Agent 可自省的白名单
# ============================================================

@dataclass
class CourseFilters:
    """
    课程查询过滤器

    Agent 可以任意组合这些字段，但不能超出这个白名单。
    所有字段都是可选的，不传则不过滤。
    """
    keyword: str | None = None           # 模糊搜索（课程名/编码/教师名）
    teacher_id: int | None = None        # 精确匹配
    course_type: CourseType | None = None
    status: CourseStatus | None = None   # 默认不过滤状态
    created_after: datetime | None = None
    created_before: datetime | None = None


# ============================================================
# QueryService
# ============================================================

class CourseQueryService(BaseQueryService):
    """课程查询服务 —— 一个方法承接所有查询"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    # ── 统一查询入口 ──

    async def query_courses(
        self,
        filters: CourseFilters | None = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str | None = None,      # "created_at" / "-created_at" 等
    ) -> PageResult:
        """
        Agent 调用课程查询的唯一入口。

        Agent 传入任意组合的 filters，内部构建 SQL 并分页返回。
        """
        filters = filters or CourseFilters()
        stmt = self._build_query(filters)

        # 排序
        stmt = self._apply_ordering(stmt, Course, order_by)

        # 分页
        return await self._paginate(stmt, page, page_size)

    # ── SQL 构建（内部）──

    def _build_query(self, f: CourseFilters) -> Select:
        """根据过滤器构建 SELECT 语句"""
        stmt = select(Course).where(Course.deleted_at.is_(None))

        if f.keyword:
            stmt = stmt.where(
                or_(
                    Course.course_name.ilike(f"%{f.keyword}%"),
                    Course.course_code.ilike(f"%{f.keyword}%"),
                    Course.teacher_name.ilike(f"%{f.keyword}%"),
                )
            )

        if f.teacher_id is not None:
            stmt = stmt.where(Course.teacher_id == f.teacher_id)

        if f.course_type is not None:
            stmt = stmt.where(Course.course_type == f.course_type.value)

        if f.status is not None:
            stmt = stmt.where(Course.status == f.status.value)

        if f.created_after is not None:
            stmt = stmt.where(Course.created_at >= f.created_after)

        if f.created_before is not None:
            stmt = stmt.where(Course.created_at <= f.created_before)

        return stmt