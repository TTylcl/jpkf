"""
core/graph/nodes/agent_node.py

Agent节点 - 调用LLM决定下一步动作
"""
import asyncio
import os
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from datetime import datetime
from langgraph.runtime import Runtime
from core.context import AgentContext
from agent.state import AgentState
from utils.logger import add_log
from langchain_core.language_models import BaseChatModel
from circuit.breaker import llm_breaker, with_circuit_breaker
from core import settings


_llm_cache: dict[str, BaseChatModel] = {}


def _get_llm(agent_role: str,tool_names:list[str] | None = None ,streaming: bool = True) -> BaseChatModel:
    """获取或创建 LLM 实例（按 role + tool_names 缓存）"""
    mode ='stream' if streaming else 'plain'
    base =  agent_role if tool_names is None else f"{agent_role}:{','.join(sorted(tool_names))}"
    cache_key = f"{base}:{mode}"
    if cache_key not in _llm_cache:
        from agent.llm import bind_tools_to_llm
        _llm_cache[cache_key] = bind_tools_to_llm(agent_role=agent_role,tool_names=tool_names, streaming=streaming)
    return _llm_cache[cache_key]


def _resolve_context(runtime: Runtime[AgentContext], config: RunnableConfig) -> AgentContext:
    """解析请求上下文：优先 Runtime，兜底从 config 构造"""
    ctx = runtime.context
    if ctx is not None:
        return ctx
    # 兜底：部分 LangGraph 版本不自动注入 context_schema
    cfg = config.get("configurable", {})
    return AgentContext(
        user_id=str(cfg.get("user_id", "")),
        agent_role=cfg.get("agent_role", ""),
        user_role=cfg.get("user_role", ""),
        trace_id=cfg.get("trace_id", ""),
        wx_openid=cfg.get("wx_openid", ""),
    )


def _llm_fallback(llm, messages):
    """LLM 熔断降级：返回一条兜底消息，让 Agent 流程优雅结束而不是崩溃"""
    return AIMessage(content=settings.CIRCUIT_DEGRADE_MESSAGE)


@with_circuit_breaker(llm_breaker, _llm_fallback)
async def _astream_collect(llm, messages):
    """流式收集 LLM 响应"""
    merged = None
    async for msg in llm.astream(messages):
        # AIMessageChunk 用 + 累加：content 拼接、tool_calls 按 index 正确合并
        merged = msg if merged is None else merged + msg
    if merged is None:
        #
        return AIMessage(content=settings.CIRCUIT_DEGRADE_MESSAGE)
    return AIMessage(content=merged.content, tool_calls=merged.tool_calls or None)


async def _invoke_llm(llm, messages,fallback_llm = None):
    """调用 LLM，带三级降级：流式 → 非流式 → 熔断"""
    timeout = float(os.getenv("LLM_TIMEOUT", "10"))
    #先流式，如果流式失败，超时换非流式调用，非流式也失败，熔断器兜底
    try:
        # 1. 流式：让 chat_stream 能逐 token 推送
        return await asyncio.wait_for(_astream_collect(llm, messages), timeout=timeout)
    except Exception as e:
        if fallback_llm is not None:
              add_log("WARNING", f"LLM 流式失败({type(e).__name__})，转非流式兜底", module="llm")
              return await asyncio.wait_for(fallback_llm.ainvoke(messages), timeout=timeout)
        #熔断降级
        raise

def create_agent_node(system_prompt: str = "",tool_names: list[str] | None = None):
    """
    构建 agent 节点。

    Agent Node 走 Runtime[AgentContext]，从请求上下文动态获取 agent_role 并绑定工具。
    运行时注入的 context_schema 为 AgentContext，包含用户信息、角色信息、请求信息等。
    args:
        system_prompt: 系统提示词，包含身份信息
        tool_names: 工具名称列表，默认为 None，表示使用默认工具
    """

    async def agent_node(
        state: AgentState,
        config: RunnableConfig,
        runtime: Runtime[AgentContext],
    ) -> dict:
        ctx = _resolve_context(runtime, config)

        llm_with_tools = _get_llm(ctx.agent_role,tool_names,streaming=True)
        llm_plain = _get_llm(ctx.agent_role,tool_names,streaming=False)  # 非流式兜底
        messages = state["messages"]

        now = datetime.now()
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        today_str = now.strftime("%Y年%m月%d日")
        weekday_str = weekday_names[now.weekday()]
        identity_hint = (
            f"\n【当前环境信息】"
            f"\n- 当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"
            f"\n-今天是：{today_str}{weekday_str}"
            f"\n【当前用户信息】"
            f"\n- 用户ID：{ctx.user_id} ← 调用任何 parent_id 参数时，都用这个值"
            f"\n- 用户角色：{ctx.user_role}"
            f"\n- 你的角色：{ctx.agent_role}"
        )
        #注入state 预加载数据 避免重复调用工具
        children_data = state.get("children_data")
        if children_data:
            child_lines = []
            for c in children_data:
                sid = c.get("student_id", "")
                sname = c.get("student_name", "")
                child_lines.append(f"  - {sname}（student_id={sid}）")
            identity_hint += (
                f"\n【预加载-孩子列表】\n" + "\n".join(child_lines) +
                f"\n（以上孩子信息已预加载，可直接使用其 student_id，"
                f"无需再调 get_my_children）"
            )
        day_of_week = state.get("day_of_week")
        if day_of_week is not None:
            dow_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            dow_str = dow_names[day_of_week] if 1 <= day_of_week <= 7 else f"day_of_week={day_of_week}"
            identity_hint += (
                f"\n- 用户关心的星期：{dow_str}（day_of_week={day_of_week}）"
                f"\n  调用 get_child_schedules 时直接传入 day_of_week={day_of_week}"
            )
        # 注入意图信息，帮助 LLM 理解用户的目标
        intent = state.get("intent") 
        # 如果有意图信息，注入到身份提示中，帮助 LLM 理解用户的目标
        if intent:
            identity_hint += f"\n- 当前任务意图：{intent}"
        dynamic_prompt = system_prompt.format(
            agent_role=ctx.agent_role,
            user_role=ctx.user_role,
        ) + identity_hint
        # 如果有动态系统提示词，且消息列表为空或首条消息不是 system 类型，则将动态系统提示词插入到消息列表开头
        if dynamic_prompt and (
            not messages or messages[0].type != "system"
        ):
            messages = [SystemMessage(content=dynamic_prompt)] + list(messages)
        # 调用 LLM
        response = await _invoke_llm(llm_with_tools, messages, fallback_llm=llm_plain)
        return {"messages": [response]}

    return agent_node