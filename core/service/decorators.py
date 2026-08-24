"""
core/service/decorators.py
工具装饰器 —— 权限 + 日志 + 脱敏 + 异常
"""

from functools import wraps
from dataclasses import dataclass, field

from core.service.models import ServiceResult, check_permission
from core.service.layers import add_service_log
from core.service.utils import mask_sensitive


@dataclass
class ToolMeta:
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    require_permission: bool = True
    sensitive_output: bool = False
    owner_param: str | None = None        # 声明"哪个参数必须等于当前登录人"
    owner_roles: tuple = ()               # 只有这些 user_role 会被强制覆盖


def tool(meta: ToolMeta):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, **params):
            tool_name = meta.name

            # 1. 权限
            if meta.require_permission:
                if not check_permission(ctx.agent_role, self.resource, tool_name):
                    add_service_log("error", f"权限不足: {ctx.agent_role} -> {tool_name}", ctx)
                    return ServiceResult.error(
                        message=f"无权调用工具: {tool_name}",
                        code=403,
                        trace_id=ctx.trace_id,
                    )

            # 1.5 归属校验（IDOR 防护）：把"我的数据"参数强制改成当前登录人
            if meta.owner_param and meta.owner_param in params and ctx.user_role in meta.owner_roles:
                params[meta.owner_param] = ctx.user_id

            # 2. 执行
            try:
                result = await func(self, ctx, **params)
                if not isinstance(result, ServiceResult):
                    result = ServiceResult.ok(data=result, trace_id=ctx.trace_id)

                # 3. 脱敏
                if meta.sensitive_output and result.data:
                    result.data = mask_sensitive(result.data, ctx.agent_role)

                add_service_log("info", f"工具 {tool_name} 执行成功", ctx)
                return result

            except Exception as e:
                add_service_log("error", f"工具 {tool_name} 执行失败: {e}", ctx)
                return ServiceResult.error(
                    message=f"执行失败: {str(e)}",
                    code=500,
                    trace_id=ctx.trace_id,
                )

        wrapper.__tool_meta__ = meta
        return wrapper

    return decorator