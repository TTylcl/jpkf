"""
service/user_service.py
用户 Service —— AI Agent 工具层
"""

from __future__ import annotations

from datetime import datetime

from core.context import CTX
from core.service.utils import get_dao
from core.service.models import ServiceResult
from core.service.decorators import tool, ToolMeta
from dal.dao.user_dao import UserDao
from dal.query.user_query_service import UserQueryService, UserFilters
from dal.query import PageResult
from dal.models.enums import UserType
from schemas.user_schema import UserResponse, UserCountResponse, UserListResponse

class UserService:
    resource = "user"
    dao_class = UserDao

    # ==================== 查询 ====================

    @tool(ToolMeta(
        name="query_users",
        description="灵活查询用户列表。支持关键词、用户类型、注册时间范围等组合过滤，支持分页和排序。",
        parameters={
            "keyword":        {"type": "string",  "description": "模糊搜索：姓名 / 用户名 / 手机号", "default": None},
            "user_type":      {"type": "string",  "description": "用户类型：TEACHER / STUDENT / PARENT", "default": None},
            "created_after":  {"type": "string",  "description": "注册时间起始（ISO 格式）", "default": None},
            "created_before": {"type": "string",  "description": "注册时间截止（ISO 格式）", "default": None},
            "page":           {"type": "integer", "default": 1},
            "page_size":      {"type": "integer", "default": 20},
            "order_by":       {"type": "string",  "description": "排序字段，- 前缀表示降序", "default": None},
        },
        require_permission=True,
        sensitive_output=True,
    ))
    async def query_users(
        self,
        ctx: CTX,
        keyword: str | None = None,
        user_type: str | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str | None = None,
    ) -> ServiceResult:
        qs = UserQueryService(ctx.session)

        filters = UserFilters(
            keyword=keyword,
            user_type=UserType(user_type) if user_type else None,
            created_after=datetime.fromisoformat(created_after) if created_after else None,
            created_before=datetime.fromisoformat(created_before) if created_before else None,
        )

        result: PageResult = await qs.query_users(filters, page=page, page_size=page_size, order_by=order_by)
        return UserListResponse(
            items=[UserResponse.from_orm_model(u) for u in result.items],
            total=result.total,
            page=page,
            page_size=page_size,
            total_pages=result.total_pages
        )

    @tool(ToolMeta(
        name="get_user",
        description="根据用户 ID 获取用户详情",
        parameters={"user_id": {"type": "integer", "description": "用户 ID"}},
        require_permission=True,
        sensitive_output=True,
    ))
    async def get_user(self, ctx: CTX, user_id: int) -> ServiceResult:
        dao: UserDao = get_dao(ctx, self.dao_class)
        user = await dao.get_by_id(user_id)
        if not user:
            return ServiceResult.error(message=f"用户#{user_id}不存在", code=404, trace_id=ctx.trace_id)
        return UserResponse.from_orm_model(user)

    @tool(ToolMeta(
        name="get_user_by_username",
        description="根据用户名查找用户",
        parameters={"username": {"type": "string", "description": "用户名"}},
        require_permission=True,
        sensitive_output=True,
    ))
    async def get_user_by_username(self, ctx: CTX, username: str) -> ServiceResult:
        dao: UserDao = get_dao(ctx, self.dao_class)
        user = await dao.get_by_username(username)
        if not user:
            return ServiceResult.error(message=f"用户名「{username}」对应的用户不存在", code=404, trace_id=ctx.trace_id)
        return UserResponse.from_orm_model(user)

    # ==================== 统计 ====================

    @tool(ToolMeta(
        name="count_users",
        description="按用户类型统计数量",
        parameters={"user_type": {"type": "string", "description": "用户类型：TEACHER / STUDENT / PARENT"}},
        require_permission=True,
    ))
    async def count_users(self, ctx: CTX, user_type: str) -> ServiceResult:
        qs = UserQueryService(ctx.session)
        count = await qs.count_by_type(UserType(user_type))
        return UserCountResponse(user_type=user_type, count=count)

    # ==================== 写入 ====================

    @tool(ToolMeta(
        name="create_user",
        description="创建新用户",
        parameters={
            "username":  {"type": "string", "description": "用户名"},
            "real_name": {"type": "string", "description": "真实姓名"},
            "user_type": {"type": "string", "description": "用户类型：TEACHER / STUDENT / PARENT"},
            "phone":     {"type": "string", "description": "手机号（可选）", "default": None},
            "email":     {"type": "string", "description": "邮箱（可选）", "default": None},
            "password":  {"type": "string", "description": "密码"},
        },
        require_permission=True,
        sensitive_output=True,
    ))
    async def create_user(
        self,
        ctx: CTX,
        username: str,
        real_name: str,
        user_type: str,
        password: str,
        phone: str | None = None,
        email: str | None = None,
    ) -> ServiceResult:
        dao: UserDao = get_dao(ctx, self.dao_class)

        if await dao.exists_by_username(username):
            return ServiceResult.error(message=f"用户名已存在: {username}", code=409, trace_id=ctx.trace_id)
        if phone and await dao.exists_by_phone(phone):
            return ServiceResult.error(message=f"手机号已被占用: {phone}", code=409, trace_id=ctx.trace_id)

        user = await dao.create(
            username=username,
            real_name=real_name,
            user_type=UserType(user_type).value,
            phone=phone,
            email=email,
        )
        return UserResponse.from_orm_model(user)
    @tool(ToolMeta(
        name="update_user",
        description="更新用户信息",
        parameters={
            "user_id":   {"type": "integer", "description": "用户 ID"},
            "real_name": {"type": "string",  "description": "真实姓名（可选）", "default": None},
            "phone":     {"type": "string",  "description": "手机号（可选）", "default": None},
            "email":     {"type": "string",  "description": "邮箱（可选）", "default": None},
        },
        require_permission=True,
        sensitive_output=True,
    ))
    async def update_user(
        self,
        ctx: CTX,
        user_id: int,
        real_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> ServiceResult:
        dao: UserDao = get_dao(ctx, self.dao_class)

        existing = await dao.get_by_id(user_id)
        if not existing:
            return ServiceResult.error(message=f"用户#{user_id}不存在", code=404, trace_id=ctx.trace_id)

        updates = {k: v for k, v in {
            "real_name": real_name,
            "phone": phone,
            "email": email,
        }.items() if v is not None}

        if not updates:
            return ServiceResult.error(message="没有需要更新的字段", code=400, trace_id=ctx.trace_id)

        user = await dao.update(user_id, **updates)
        return UserResponse.from_orm_model(user)

    @tool(ToolMeta(
        name="delete_user",
        description="软删除用户",
        parameters={"user_id": {"type": "integer", "description": "用户 ID"}},
        require_permission=True,
    ))
    async def delete_user(self, ctx: CTX, user_id: int) -> ServiceResult:
        dao: UserDao = get_dao(ctx, self.dao_class)

        existing = await dao.get_by_id(user_id)
        if not existing:
            return ServiceResult.error(message=f"用户#{user_id}不存在", code=404, trace_id=ctx.trace_id)

        await dao.soft_delete(user_id)
        return ServiceResult.ok(data=None, trace_id=ctx.trace_id, message=f"用户#{user_id}已删除")