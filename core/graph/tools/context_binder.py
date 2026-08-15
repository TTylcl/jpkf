"""
上下文注入器
职责：从 LangGraph 的 RunnableConfig 中提取 CTX（session、agent_role、trace_id），
      通过闭包将 CTX 注入到 Service 方法的第一个参数，确保每次工具调用携带正确的
      数据库会话和权限信息。
"""
from __future__ import annotations
from typing import Any
from langchain_core.runnables import RunnableConfig
from core.context import CTX
from core.database import AsyncDatabase

def bind_ctx_to_tool(method: Any) -> Any:
    """
    给工具方法包装一层，从 RunnableConfig 中提取 CTX 并注入
    
    Args:
        method: Service 层的 @tool 装饰的异步方法
    
    Returns:
        包装后的异步函数，符合 LangChain StructuredTool 的 coroutine 签名：
        async def fn(call_input: Any, config: RunnableConfig) -> Any
    """
    async def tool_coroutine(config: RunnableConfig, **call_input: Any) -> Any:
        
        #1 从 config 中提取 CTX 不包含数据库链接
        configurable = config.get("configurable", {}) # 从 RunnableConfig 中提取 configurable
        user_id = configurable.get("user_id") # 从 用户
        user_role = configurable.get("user_role") # 从 用户角色
        agent_role = configurable.get("agent_role") # 从 代理角色
        trace_id = configurable.get("trace_id")     # 追踪id
        #2校验
        if user_id is None:
            raise ValueError(
                "用户ID不能为空 "
                " Ensure user_id is passed via 'configurable' when invoking the graph.")
        if call_input is None:
            call_input = {}
        #call_inpout转字典
        if isinstance(call_input, dict): #如果pydantic模型是字典
            call_input = call_input  # 直接使用字典
        else:        # 如果是 pydantic 模型
            call_input = call_input.model_dump()   # 转为字典
        #开启一个数据库会话，拼接ctx对象
        async with AsyncDatabase.get_session() as session:
            ctx = CTX(
                user_id=user_id,
                user_role=user_role,
                agent_role=agent_role,
                session=session,
                trace_id=trace_id,
                wx_openid="", # 微信openid
                
            )
            try:
                return await method(ctx,**call_input)
            except Exception as e:
                    import traceback
                    print(f"=== TOOL ERROR: {e}")
                    traceback.print_exc()
                    raise
            #调用方法
    return tool_coroutine


__all__ = ["bind_ctx_to_tool"]