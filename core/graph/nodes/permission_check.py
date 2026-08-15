"""
权限校验节点（前置拦截器）

职责：在意图分类和路由之前，先检查用户是否有权使用系统。        这是整个 Agent Router 架构的第一道关卡。

设计原则：
1. 快速失败 —— 快速返回，不执行后续节点
2. 失败即终止 —— 权限不足时直接写入系统消息并路由到 END
3. 粗粒度拦截 —— 只判断"能不能用系统"，细粒度权限仍由 ToolNode 的
AGENT_PERMISSIONS_MATRIX 保障
4. 双通道获取身份 —— 优先 Runtime[AgentContext]，兜底从 config 构造
"""
from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from agent.state import AgentState
from core.context import AgentContext

# ── 允许使用系统的用户角色白名单 ──
ALLOWED_USER_ROLES = frozenset({"parent", "student", "teacher", "admin"})

# ── 允许使用系统的 Agent 角色白名单 ──
ALLOWED_AGENT_ROLES = frozenset({
    "customer_service_agent",
    "edu_admin_agent",
    "teacher_agent",
    "student_agent",
})

def _resolve_context(
    runtime: Runtime[AgentContext],
    config: RunnableConfig,
) -> AgentContext:
    """
        解析请求上下文。

        优先从 Runtime 获取（LangGraph 自动注入 context_schema），
        如果 Runtime 为空（部分版本不自动注入），则从 config.configurable 兜底构造。
    """
    ctx = runtime.context
    if ctx is not None:  #当在runtime中运行时，ctx不为空时
        return ctx   #   直接返回Runtime

    cfg = config.get("configurable", {})
    return AgentContext(
        user_id=str(cfg.get("user_id", "")),
        agent_role=cfg.get("agent_role", ""),
        user_role=cfg.get("user_role", ""),
        trace_id=cfg.get("trace_id", ""),
        wx_openid=cfg.get("wx_openid", ""),
    )

def _build_deny_message(reason: str) -> str:
      """构造权限拒绝时的用户提示消息。"""
      return (
          f"抱歉，您暂时无法使用此服务。\n\n"
          f"原因：{reason}\n\n"
          f"如有疑问，请联系客服。"
      )


async def permission_check_node(
      state: AgentState,
      config: RunnableConfig,
      runtime: Runtime[AgentContext],
  ) -> dict:
    """
    权限校验节点。

    校验逻辑（按顺序）：
    1. user_role 是否在白名单中
    2. agent_role 是否在白名单中
    3. user_id 是否合法（> 0）

    通过 → 原样返回空 dict，state 不变，继续流转到 classify_intent
    拒绝 → 返回 {"messages": [AIMessage], "permission_denied": True}，路由终止

    Args:
        state: 当前 AgentState（含 messages, user_id, user_role, agent_role）
        config: LangGraph RunnableConfig（含 configurable 字段）
        runtime: LangGraph Runtime，自动注入 AgentContext

    Returns:
        dict: 通过时返回 {}（不修改 state），拒绝时返回 AIMessage + permission_denied 标记    
    """
    ctx = _resolve_context(runtime, config)   

    # ── 校验 1：user_role 合法性 ──
    if not ctx.user_role:
        return {
            "messages":[AIMessage(content=_build_deny_message("未识别到用户身份。"))],
            "permission_denied": True,
        }
    if ctx.user_role not in ALLOWED_USER_ROLES:
          return {
              "messages": [AIMessage(content=_build_deny_message(
                  f"用户角色 '{ctx.user_role}' 不在允许范围内。"
              ))],
              "permission_denied": True,
          }
    # ── 校验 2：agent_role 合法性 ──
    if not ctx.agent_role:
        return {
            "messages":[AIMessage(content=_build_deny_message("未配置智能体角色。"))],
            "permission_denied": True,
        }

    if ctx.agent_role not in ALLOWED_AGENT_ROLES:
        return {
            "messages": [AIMessage(content=_build_deny_message(f"智能体角色 '{ctx.agent_role}' 未注册。"))],
            "permission_denied": True,
        }

    # ── 校验 3：user_id 合法性 ──
    try:
        uid = int(ctx.user_id)
    except (ValueError, TypeError):
        return {
            "messages": [AIMessage(content=_build_deny_message("用户 ID格式无效。"))],
            "permission_denied": True,
        }

    if uid <= 0:
        return {
            "messages": [AIMessage(content=_build_deny_message("用户 ID无效。"))],
            "permission_denied": True,
        }

    # ── 全部通过，放行 ──
    return {} #返回空字典，不需要加别的动，继续流转到 classify_intent








