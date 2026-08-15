"""
预取节点 —— 在意图分类之前预加载 parent 的孩子数据

职责：permission_check 通过后，在 classify_intent 之前，
      为 parent 角色预取 children_data 写入 state。

为什么需要：
  classify_intent_node 的维度2（用户画像注入）通过 state.get("children_data")
  读取孩子列表，但没有任何节点写入此字段 → 孩子姓名永远显示"未获取"。
  本节点填补这个缺口。

设计原则：
  1. 只读 Runtime 身份，写 state —— 不调 LLM，不查权限矩阵
  2. 按需取 —— 非 parent 直通，不浪费 DB 查询
  3. 静默降级 —— DB 异常时写空列表，不阻塞后续流程
  4. 自己管理 session —— 不依赖全局连接，用完即关
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from agent.state import AgentState
from core.context import AgentContext
from core.database import AsyncDatabase


def _resolve_context(
    runtime: Runtime[AgentContext],
    config: RunnableConfig,
) -> AgentContext:
    """解析请求上下文：优先 Runtime，兜底从 config 构造。"""
    ctx = runtime.context
    if ctx is not None:
        return ctx

    cfg = config.get("configurable", {})
    return AgentContext(
        user_id=str(cfg.get("user_id", "")),
        agent_role=cfg.get("agent_role", ""),
        user_role=cfg.get("user_role", ""),
        trace_id=cfg.get("trace_id", ""),
        wx_openid=cfg.get("wx_openid", ""),
    )


async def prefetch_children_node(
    state: AgentState,
    config: RunnableConfig,
    runtime: Runtime[AgentContext],
) -> dict:
    """
    预取 parent 绑定的孩子列表，写入 state.children_data。

    流程：
    1. 取 user_role 和 user_id
    2. 非 parent 或无 user_id → 直通，返回 {}
    3. parent → 开 DB session → 查 ParentStudentDao → 对每个
       student_id 查 UserDao 取 real_name → 构建 children_data
    4. DB 异常 → 静默降级，返回 {"children_data": []}

    Args:
        state: 当前 AgentState
        config: LangGraph RunnableConfig
        runtime: LangGraph Runtime[AgentContext]

    Returns:
        dict: {"children_data": [...]} 或 {}（非 parent）或 {"children_data": []}（异常降级）
    """
    ctx = _resolve_context(runtime, config)

    # ── 非 parent 短路 ──
    if ctx.user_role != "parent":
        return {}

    # ── user_id 有效性 ──
    try:
        parent_id = int(ctx.user_id)
    except (ValueError, TypeError):
        return {"children_data": []}

    if parent_id <= 0:
        return {"children_data": []}

    # ── 查库：parent_id → 孩子列表 ──
    try:
        from dal.dao.parent_student_dao import ParentStudentDao
        from dal.dao.user_dao import UserDao

        async with AsyncDatabase.get_session() as session:
            # 1. 查家长绑定的所有学生
            parent_dao = ParentStudentDao(session)
            bindings = await parent_dao.get_parent_students(parent_id)

            if not bindings:
                return {"children_data": []}

            # 2. 逐个查学生姓名
            user_dao = UserDao(session)
            children_data: list[dict] = []
            for b in bindings:
                student = await user_dao.find_one(user_id=b.student_id)
                student_name = (
                    student.real_name or ""
                    if student and student.real_name
                    else f"学生ID:{b.student_id}"
                )
                children_data.append({
                    "student_id": b.student_id,
                    "student_name": student_name,
                })

            return {"children_data": children_data}

    except Exception:
        # DB 挂了或其他异常 → 静默降级，不阻塞后续流程
        # classify_intent 会把孩子名显示为"未获取"，不影响 LLM 分类结果
        return {"children_data": []}
