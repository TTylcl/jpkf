"""
Tool Node - 权限与错误处理
职责：捕获工具返回的 ServiceResult（尤其是 code=403 权限拒绝），
      将其转换为自然语言错误消息返回给 LLM，避免流程中断；
      统一处理 500 异常等。
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from typing import Any
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage
from langchain_core.tools import ToolException
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from core.context import AgentContext
from utils.logger import add_log

# 从 tools/loader.py 导入工具加载器
from core.graph.tools.loader import build_langchain_tools
#缓存
_tool_node_cache: dict[str, ToolNode] = {}

def _get_tool_node(agent_role: str | None = None) -> ToolNode:
    """
    获取 Tool Node

    Args:
        agent_role: 可选，按角色过滤工具（None = 不过滤）

    Returns:
        ToolNode: Tool Node 对象
    """
    if agent_role not in _tool_node_cache: # 缓存
        tools = build_langchain_tools(agent_role=agent_role)
        _tool_node_cache[agent_role] = ToolNode( # 创建 ToolNode
            tools, # 工具列表
            handle_tool_errors=_handle_service_result, #
        )
    return _tool_node_cache[agent_role] # 返回

def _resolve_agent_role(runtime: Runtime[AgentContext], config: RunnableConfig) -> str:
    """解析 agent_role：优先 Runtime，兜底从 config 构造"""
    ctx = runtime.context
    if ctx is not None:
        return ctx.agent_role
    cfg = config.get("configurable", {})
    return cfg.get("agent_role", "")


async def dynamic_tool_node(
        state: dict,
        config: RunnableConfig,
        runtime: Runtime[AgentContext],
) -> dict:
    """
    动态创建 Tool Node

    Args:
        state: 状态字典
        config: 透传 context_binder
        runtime: 只用于拿 agent_role 选 ToolNode

    Returns:
        dict: 运行结果
    """
    agent_role = _resolve_agent_role(runtime, config)
    tool_node = _get_tool_node(agent_role)
    return await tool_node.ainvoke(state, config)




def _handle_service_result(error: Exception) -> ToolMessage:
    """
    处理 ServiceResult 类型的错误
    重点处理 code=403 权限拒绝，转换为自然语言
    """
    # 如果是 ServiceResult 类型（有 code 和 message 属性）
    if hasattr(error, 'code') and hasattr(error, 'message'):
        code = error.code
        message = error.message
        
        # 403 权限拒绝
        if code == 403:
            return ToolMessage(
                content=f"❌ 权限不足：{message}\n\n请确认你是否有权限执行此操作。",
                name=error.name if hasattr(error, 'name') else "unknown_tool",
                tool_call_id=error.tool_call_id if hasattr(error, 'tool_call_id') else "unknown_id",
            )
        
        # 404 资源不存在
        if code == 404:
            return ToolMessage(
                content=f"❌ 资源不存在：{message}\n\n请检查查询条件是否正确。",
                name=error.name if hasattr(error, 'name') else "unknown_tool",
                tool_call_id=error.tool_call_id if hasattr(error, 'tool_call_id') else "unknown_id",
            )
        
        # 409 业务冲突
        if code == 409:
            return ToolMessage(
                content=f"❌ 操作冲突：{message}\n\n请稍后重试或联系管理员。",
                name=error.name if hasattr(error, 'name') else "unknown_tool",
                tool_call_id=error.tool_call_id if hasattr(error, 'tool_call_id') else "unknown_id",
            )
        
        # 其他已知错误码
        return ToolMessage(
            content=f"❌ 操作失败（{code}）：{message}",
            name=error.name if hasattr(error, 'name') else "unknown_tool",
            tool_call_id=error.tool_call_id if hasattr(error, 'tool_call_id') else "unknown_id",
        )
    
    # 如果是 ToolException 或其他异常
    return ToolMessage(
        content=f"❌ 系统异常：{str(error)}\n\n请稍后重试或联系技术支持。",
        name="unknown_tool",
        tool_call_id="unknown_id",
    )


def create_service_tool_node(agent_role: str | None = None) -> tuple[ToolNode, list]:
    """
    创建带错误处理的 Tool Node

    Args:
        agent_role: 可选，按角色过滤工具（None = 不过滤）

    Returns:
        tuple: (tool_node, tools) - ToolNode 对象和工具列表
    """
    add_log("INFO", f"构建 Tool Node (agent_role={agent_role or 'all'})", module="graph")

    # 1. 加载工具（按角色过滤）
    tools = build_langchain_tools(agent_role=agent_role)

    # 2. 创建带错误处理的 ToolNode
    tool_node = ToolNode(
        tools,
        handle_tool_errors=_handle_service_result,  # ✅ 统一错误处理
    )

    add_log("INFO", "ToolNode 构建成功（带 403/404/500 错误处理）", module="graph")

    return tool_node, tools


__all__ = ["create_service_tool_node"]


# 单独运行测试
if __name__ == "__main__":
    tool_node, tools = create_service_tool_node()