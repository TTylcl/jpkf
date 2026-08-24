"""
功能：Agent Router 图结构设计
职责：构建 LangGraph StateGraph，实现 Router 架构：
    permission_check → prefetch_children → classify_intent → 角色路由 → 六路 Agent 节点

核心目标：注意力隔离 —— 让 LLM 在不同任务下看到不同的 prompt 和工具集。

架构：
  START
    │
    ▼
  permission_check ──(denied)──► END
    │(ok)
    ▼
  classify_intent
    │
    ▼
  route_by_role_and_intent
    │
    ├── parent + schedule → schedule_agent ⇄ tools
    ├── parent + course   → course_rag_agent ⇄ tools
    ├── parent + general  → parent_service_agent ⇄ tools
    ├── admin             → admin_agent ⇄ tools
    ├── teacher           → teacher_agent ⇄ tools
    └── student           → student_agent ⇄ tools

设计要点：
六个 agent 节点按角色+意图拆分，每个角色只看到自己需要的 prompt 和工具集。
非 parent 角色在 classify_intent 层短路到 general，图路由层按 agent_role 二次分发到对应角色 agent。
parent 角色走意图三分支：排课查询 / 课程咨询 / 通用服务。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Literal

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from agent.state import AgentState
from core.context import AgentContext
from core.graph.nodes.agent_node import create_agent_node
from core.graph.nodes.tool_node import dynamic_tool_node
from core.graph.nodes.classify_intent import classify_intent_node
from core.graph.nodes.permission_check import permission_check_node
from core.graph.nodes.prefetch_node import prefetch_children_node
from langchain_core.messages import ToolMessage
from core.prompt_templates.base_templates import (
    ADMIN_PROMPT,
    TEACHER_PROMPT,
    PARENT_SERVICE_PROMPT,
    STUDENT_PROMPT,
    SCHEDULE_AGENT_PROMPT,
    RAG_AGENT_PROMPT,
)
from utils.logger import add_log

# ══════════════════════════════════════════════════════════════
# 工具白名单映射（intent → tool_names）
# 与 agent_role 权限矩阵取交集，双重保障
# ══════════════════════════════════════════════════════════════

INTENT_TOOL_MAP: dict[str, list[str] | None] = {
    "parent_schedule": ["get_my_children", "get_child_schedules"],
    "parent_course":   ["rag_search", "get_child_courses", "get_my_children",
                        "query_courses", "get_course"],
    "general":         None,   # None = 走 agent_role 全量权限工具
}

# ══════════════════════════════════════════════════════════════
# 单例缓存
# ══════════════════════════════════════════════════════════════

_graph: StateGraph | None = None


def get_agent_graph() -> StateGraph:
    """获取 agent graph（模块级单例缓存）"""
    global _graph
    if _graph is None:
        _graph = build_router_graph()
    return _graph


# ── 兼容旧接口 ──

def build_agent_graph() -> StateGraph:
    """[deprecated] 使用 build_router_graph() 代替"""
    return build_router_graph()


# ══════════════════════════════════════════════════════════════
# Router 图构建
# ══════════════════════════════════════════════════════════════

def build_router_graph() -> StateGraph:
    """
    构建 Agent Router 图。

    数据流（一个完整请求的 state 变化）：

      请求进入  state = {messages: [HumanMessage("小明今天有课吗")],
                         user_id: 9, user_role: "parent",
                         agent_role: "customer_service_agent"}

      permission_check → state 不变（通过，返回 {}）

      classify_intent  → state += {intent: "parent_schedule", day_of_week: None}

      route_by_intent  → 读 intent → 路由到 schedule_agent

      schedule_agent 第1轮  → tool_call: get_my_children(parent_id=9)
      tools 第1轮           → state.messages += [ToolMessage(孩子列表)]
      schedule_agent 第2轮  → tool_calls: [get_child_schedules(小明),
                                           get_child_schedules(小红)]
      tools 第2轮           → state.messages += [ToolMessage(小明排课),
                                                 ToolMessage(小红排课)]
      schedule_agent 第3轮  → state.messages += [AIMessage("小明今天下午3:00有
                                                           钢琴课...")]

      返回用户  最终 AIMessage 即为用户看到的回复
    """
    add_log("INFO", "构建 Agent Router 图（permission → classify → 角色路由 → 6 Agent）", module="graph")

    # ── 1. 初始化 StateGraph ──
    graph = StateGraph(AgentState, context_schema=AgentContext)

    # ── 2. 创建六个 Agent 节点 ──
    #      按角色 + 意图拆分，每个节点独立的 prompt + 工具白名单

    schedule_agent_node = create_agent_node(
        system_prompt=SCHEDULE_AGENT_PROMPT,
        tool_names=INTENT_TOOL_MAP["parent_schedule"],
    )
    course_rag_agent_node = create_agent_node(
        system_prompt=RAG_AGENT_PROMPT,
        tool_names=INTENT_TOOL_MAP["parent_course"],
    )
    # 家长通用（咨询、绑定、预排课引导）
    parent_service_agent_node = create_agent_node(
        system_prompt=PARENT_SERVICE_PROMPT,
        tool_names=INTENT_TOOL_MAP["general"],
    )
    # 教务管理员
    admin_agent_node = create_agent_node(
        system_prompt=ADMIN_PROMPT,
        tool_names=None,
    )
    # 教师
    teacher_agent_node = create_agent_node(
        system_prompt=TEACHER_PROMPT,
        tool_names=None,
    )
    # 学生
    student_agent_node = create_agent_node(
        system_prompt=STUDENT_PROMPT,
        tool_names=None,
    )

    # ── 3. 注册所有节点 ──
    graph.add_node("permission_check", permission_check_node)
    graph.add_node("prefetch_children", prefetch_children_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("schedule_agent", schedule_agent_node)
    graph.add_node("course_rag_agent", course_rag_agent_node)
    graph.add_node("parent_service_agent", parent_service_agent_node)
    graph.add_node("admin_agent", admin_agent_node)
    graph.add_node("teacher_agent", teacher_agent_node)
    graph.add_node("student_agent", student_agent_node)
    graph.add_node("tools", dynamic_tool_node)

    # ── 4. 入口 → 权限校验 ──
    graph.add_edge(START, "permission_check")

    # ── 5. 权限校验 → 拒绝短路 / 放行到预取 → 意图分类 ──
    def route_after_permission(state: AgentState) -> Literal["prefetch_children", "__end__"]:
        """权限被拒绝时直接短路到 END；通过则先预取孩子数据再分类"""
        if state.get("permission_denied"):
            return "__end__"
        return "prefetch_children"

    graph.add_conditional_edges(
        "permission_check",
        route_after_permission,
        {"prefetch_children": "prefetch_children", "__end__": END},
    )

    # ── 5.5 预取完成 → 意图分类 ──
    graph.add_edge("prefetch_children", "classify_intent")

    # ── 6. 意图分类 → 按角色+意图路由 ──
    def route_by_role_and_intent(state: AgentState) -> Literal[
        "schedule_agent", "course_rag_agent", "parent_service_agent",
        "admin_agent", "teacher_agent", "student_agent", "__end__"
    ]:
        """按 agent_role + intent 决定去向。
        - parent：走意图路由（schedule / course / general）
        - 非 parent：直接走角色路由（admin / teacher / student）
        """
        if state.get("permission_denied"):
            return "__end__"
        agent_role = state.get("agent_role", "")
        intent = state.get("intent", "general")

        # 家长/客服 → 按意图三分支
        if agent_role == "customer_service_agent":
            if intent == "parent_schedule":
                return "schedule_agent"
            elif intent == "parent_course":
                return "course_rag_agent"
            else:
                return "parent_service_agent"

        # 教务管理员
        if agent_role == "edu_admin_agent":
            return "admin_agent"

        # 教师
        if agent_role == "teacher_agent":
            return "teacher_agent"

        # 学生
        if agent_role == "student_agent":
            return "student_agent"

        # 兜底：未知角色走家长客服
        return "parent_service_agent"

    graph.add_conditional_edges(
        "classify_intent",
        route_by_role_and_intent,
        {
            "schedule_agent": "schedule_agent",
            "course_rag_agent": "course_rag_agent",
            "parent_service_agent": "parent_service_agent",
            "admin_agent": "admin_agent",
            "teacher_agent": "teacher_agent",
            "student_agent": "student_agent",
            "__end__": END,
        },
    )

    # ── 7. 各 Agent → tools / 反思回环 / END ──
    def make_should_continue(agent_name: str):
        def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
            """LLM 发出了 tool_calls → 走 tools；无 tool_calls → END"""
            messages = state.get("messages", [])
            #每次工具最多执行10次
            t_count = sum(1 for m in messages if isinstance(m,ToolMessage))
            
            if t_count >= 10: 
                return "__end__"
     
            if not messages:
                return "__end__"
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return "__end__"
        return should_continue

    for agent_name in ("schedule_agent", "course_rag_agent", "parent_service_agent",
                       "admin_agent", "teacher_agent", "student_agent"):
        graph.add_conditional_edges(
            agent_name,
            make_should_continue(agent_name),
            {"tools": "tools", agent_name: agent_name, "__end__": END},
        )

    # ── 8. 工具节点 → 按角色+意图回到对应 Agent（ReAct 循环）──
    def route_after_tools(state: AgentState) -> Literal[
        "schedule_agent", "course_rag_agent", "parent_service_agent",
        "admin_agent", "teacher_agent", "student_agent"
    ]:
        """工具执行完毕后，按 agent_role + intent 回到对应 Agent 节点"""
        agent_role = state.get("agent_role", "")
        intent = state.get("intent", "general")

        if agent_role == "customer_service_agent":
            if intent == "parent_schedule":
                return "schedule_agent"
            elif intent == "parent_course":
                return "course_rag_agent"
            return "parent_service_agent"

        if agent_role == "edu_admin_agent":
            return "admin_agent"
        if agent_role == "teacher_agent":
            return "teacher_agent"
        if agent_role == "student_agent":
            return "student_agent"

        return "parent_service_agent"

    graph.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "schedule_agent": "schedule_agent",
            "course_rag_agent": "course_rag_agent",
            "parent_service_agent": "parent_service_agent",
            "admin_agent": "admin_agent",
            "teacher_agent": "teacher_agent",
            "student_agent": "student_agent",
        },
    )

    # ── 9. 编译 ──
    memory = MemorySaver()
    app = graph.compile(checkpointer=memory)

    add_log("INFO", "Agent Router 图构建成功: permission_check → classify_intent → 角色路由", module="graph")

    return app


# ══════════════════════════════════════════════════════════════
# 单独运行测试
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import HumanMessage

    async def _test_router():
        app = get_agent_graph()

        base_configurable = {
            "thread_id": "test_router",
            "user_id": "9",
            "user_role": "parent",
            "agent_role": "customer_service_agent",
            "trace_id": "test_router",
            "wx_openid": "",
        }

        # 测试 1：排课意图 → schedule_agent
        print("\n" + "=" * 60)
        print("📋 测试 1：排课意图 → parent_schedule")
        print("=" * 60)
        print("💬 用户：小明今天有课吗？")
        result = await app.ainvoke(
            {"messages": [HumanMessage(content="小明今天有课吗？")]},
            config={"configurable": base_configurable},
        )
        print(f"📌 分类意图：{result.get('intent', 'unknown')}")
        print(f"🤖 回复：{result['messages'][-1].content[:200]}...")

        # 测试 2：课程意图 → course_rag_agent
        print("\n" + "=" * 60)
        print("📋 测试 2：课程意图 → parent_course")
        print("=" * 60)
        print("💬 用户：有什么课程？")
        cfg2 = {"configurable": {**base_configurable, "thread_id": "test_router_2"}}
        result2 = await app.ainvoke(
            {"messages": [HumanMessage(content="有什么课程？")]},
            config=cfg2,
        )
        print(f"📌 分类意图：{result2.get('intent', 'unknown')}")
        print(f"🤖 回复：{result2['messages'][-1].content[:200]}...")

        # 测试 3：通用意图 → parent_service_agent（家长）
        print("\n" + "=" * 60)
        print("📋 测试 3：通用意图 → parent_service_agent")
        print("=" * 60)
        print("💬 用户：你好，退费要多久？")
        cfg3 = {"configurable": {**base_configurable, "thread_id": "test_router_3"}}
        result3 = await app.ainvoke(
            {"messages": [HumanMessage(content="你好，退费要多久？")]},
            config=cfg3,
        )
        print(f"📌 分类意图：{result3.get('intent', 'unknown')}")
        print(f"🤖 回复：{result3['messages'][-1].content[:200]}...")

        print("\n✅ Agent Router 全部测试完成")

    asyncio.run(_test_router())
