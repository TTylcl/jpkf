"""
core/graph/nodes/agent_node.py

Agent节点 - 调用LLM决定下一步动作
"""
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from datetime import datetime
from langgraph.runtime import Runtime
from core.context import AgentContext
from agent.state import AgentState

from langchain_core.language_models import BaseChatModel


_llm_cache: dict[str, BaseChatModel] = {}


def _get_llm(agent_role: str,tool_names:list[str] | None = None ) -> BaseChatModel:
    """获取或创建 LLM 实例（按 role + tool_names 缓存）"""
    cache_key = agent_role if tool_names is None else f"{agent_role}:{','.join(sorted(tool_names))}"
    if cache_key not in _llm_cache:
        from agent.llm import bind_tools_to_llm
        _llm_cache[cache_key] = bind_tools_to_llm(agent_role=agent_role,tool_names=tool_names)
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

        llm_with_tools = _get_llm(ctx.agent_role,tool_names)
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
        intent = state.get("intent")
        if intent:
            identity_hint += f"\n- 当前任务意图：{intent}"
        dynamic_prompt = system_prompt.format(
            agent_role=ctx.agent_role,
            user_role=ctx.user_role,
        ) + identity_hint

        if dynamic_prompt and (
            not messages or messages[0].type != "system"
        ):
            messages = [SystemMessage(content=dynamic_prompt)] + list(messages)

        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    return agent_node