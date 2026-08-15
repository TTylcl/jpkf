"""
core/service/layers.py
Service 层工具函数

删掉了所有类包装，只保留真正被调用的函数。
"""

from core.context import CTX
from utils.logger import add_log


def add_service_log(level: str, message: str, ctx: CTX, module: str = "Service"):
    """统一日志输出 —— @tool 装饰器在用"""
    add_log(level=level, message=message, module=module, ctx=ctx)


def validate_pagination(page: int, page_size: int) -> str | None:
    """分页参数校验 —— 需要时直接调"""
    if page <= 0:
        return "分页必须 > 0"
    if page_size <= 0:
        return "每页条数必须 > 0"
    if page_size > 100:
        return "每页条数不能超过 100"
    return None