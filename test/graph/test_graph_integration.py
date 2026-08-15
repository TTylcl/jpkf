import uuid
import pytest
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy import text


from core.database import AsyncDatabase
from core.graph.builder import build_agent_graph

 # ═════════════════ helpers ═════════════════

def make_config(user_id="9", role="parent", thread_id=None):
    agent_role_map = {
        "parent":  "customer_service_agent",
        "student": "student_agent",
        "teacher": "teacher_agent",
        "admin":   "edu_admin_agent",
    }
    return {
        "configurable": {
            "thread_id": thread_id or str(uuid.uuid4()),
            "user_id": user_id,
            "user_role": role,
            "agent_role": agent_role_map.get(role, "customer_service_agent"),
            "trace_id": f"test-{thread_id or uuid.uuid4()}",
        },
    }

def _get_tool_calls(result: dict) -> list[dict]: 
      calls = []
      for m in result.get("messages", []):
          if hasattr(m, "tool_calls") and m.tool_calls:
              for tc in m.tool_calls:
                  calls.append({"name": tc.get("name", ""), "args": tc.get("args", {})})
      return calls

def _get_last_ai(result: dict):
    for m in reversed(result.get("messages", [])):
        if isinstance(m, AIMessage) and not (
            hasattr(m, "tool_calls") and m.tool_calls
        ):
            return m
    return None

async def _db_available() -> bool:
    try:
        async with AsyncDatabase.get_session() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
# ═════════════════ fixtures ═════════════════

@pytest.fixture
def graph():
    import core.graph.builder as _b
    _b._graph = None  # 清缓存
    return build_agent_graph()

# ═════════════════ 1. 图构建 ═════════════════

def test_graph_builds(graph):
    assert graph is not None


# ═════════════════ 2. 旧测试适配 ═════════════════

@pytest.mark.asyncio
async def test_simple_greeting(graph):
    """简单问候，student 角色走 general"""
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="你好")]},
        config=make_config(role="student"),
    )
    last = _get_last_ai(result)
    assert last is not None
    assert len(last.content) > 0

@pytest.mark.asyncio
async def test_tool_call_query_user(graph):
    """查用户信息，触发工具调用"""
    if not await _db_available():
        pytest.skip("测试数据库不可用")
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="查询用户ID为1的信息")]},
        config=make_config(role="admin"),
    )
    has_tool = any(m.type == "tool" for m in result["messages"])
    assert has_tool, "应该触发了工具调用"
    last = _get_last_ai(result)
    assert last is not None


@pytest.mark.asyncio
async def test_tool_call_list_students(graph):
    """列出学生"""
    if not await _db_available():
        pytest.skip("测试数据库不可用")
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="列出所有学生")]},
        config=make_config(role="admin"),
    )
    has_tool = any(m.type == "tool" for m in result["messages"])
    assert has_tool
    last = _get_last_ai(result)
    assert last is not None
# ═════════════════ 3. 权限拒绝 ═════════════════

@pytest.mark.asyncio
async def test_permission_denied_short_circuit(graph):
    """非法角色被拦截，不进 classify_intent"""
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="你好")]},
        config=make_config(role="hacker"),
    )
    assert result.get("permission_denied") is True
    assert result.get("intent") is None  # 没进分类
    assert "抱歉" in result["messages"][-1].content

# ═════════════════ 4. Router 三路路由 ═════════════════

@pytest.mark.asyncio
async def test_router_schedule_intent(graph):
    """排课：intent=parent_schedule，调 get_my_children + get_child_schedules"""
    if not await _db_available():
        pytest.skip("测试数据库不可用")

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="小明今天有课吗？")]},
        config=make_config(role="parent", thread_id="test-sched"),
    )
    assert result.get("intent") is not None

    tool_names = [tc["name"] for tc in _get_tool_calls(result)]
    assert "get_my_children" in tool_names, f"工具调用: {tool_names}"

    children = result.get("children_data")
    assert children is not None, "prefetch_node 应写入 children_data"

    last = _get_last_ai(result)
    assert last is not None

@pytest.mark.asyncio
async def test_router_course_intent(graph):
    """课程：intent=parent_course，调 rag_search"""
    if not await _db_available():
        pytest.skip("测试数据库不可用")

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="有什么课程？")]},
        config=make_config(role="parent", thread_id="test-course"),
    )
    assert result.get("intent") is not None

    tool_names = [tc["name"] for tc in _get_tool_calls(result)]
    assert len(tool_names) > 0, "应该有 RAG 工具调用"

    last = _get_last_ai(result)
    assert last is not None


@pytest.mark.asyncio
async def test_router_general_intent(graph):
    """通用：intent=general"""
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="你好，退费要多久？")]},
        config=make_config(role="parent", thread_id="test-gen"),
    )
    assert result.get("intent") == "general"
    last = _get_last_ai(result)
    assert last is not None


# ═════════════════ 5. P2 意图复用 ═════════════════

@pytest.mark.asyncio
async def test_p2_intent_reuse(graph):
    """同一 thread 两轮对话，第2轮复用第1轮 intent"""
    if not await _db_available():
        pytest.skip("测试数据库不可用")

    config = make_config(role="parent", thread_id="test-p2")

    r1 = await graph.ainvoke(
        {"messages": [HumanMessage(content="查一下孩子的课表")]},
        config=config,
    )
    intent1 = r1.get("intent")

    r2 = await graph.ainvoke(
        {"messages": [HumanMessage(content="那明天呢？")]},
        config=config,
    )
    intent2 = r2.get("intent")

    assert intent2 == intent1, f"意图应复用: {intent1} → {intent2}"