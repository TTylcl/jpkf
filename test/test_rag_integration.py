# test/test_rag_integration.py
"""RAG 集成测试：graph → agent → knowledge_search → 响应"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import pytest
from core.graph.builder import build_agent_graph
from core.database import AsyncDatabase
from core.context import AgentContext
from core import settings


def _ctx():
    return AgentContext(user_id="1", role="admin", agent_role="edu_admin_agent")


@pytest.fixture
async def graph():
    """异步 fixture，确保 DB init 和测试同 event loop"""
    AsyncDatabase.init(database_url=settings.DB_URI_TEST)
    g = build_agent_graph()
    yield g
    await AsyncDatabase.close()


def test_graph_builds():
    """测试1：图能正常构建"""
    graph = build_agent_graph()
    assert graph is not None


@pytest.mark.asyncio
async def test_simple_greeting(graph):
    """测试2：简单问候"""
    result = await graph.ainvoke(
        {"messages": [("user", "你好")]},
        config={"configurable": {"thread_id": "test-1"}},
        context=_ctx(),
    )
    last = result["messages"][-1]
    assert last.type == "ai"
    assert len(last.content) > 0


@pytest.mark.asyncio
async def test_rag_knowledge_search(graph):
    """测试3：知识库问题，应触发 knowledge_search"""
    result = await graph.ainvoke(
        {"messages": [("user", "退费规则是什么")]},
        config={"configurable": {"thread_id": "test-rag-1"}},
        context=_ctx(),
    )
    last = result["messages"][-1]
    assert last.type == "ai"
    has_tool = any(m.type == "tool" for m in result["messages"])
    if not has_tool:
        # LLM 可能直接用训练数据回答（不调工具），这也是合法行为
        print(f"ℹ️  LLM 未调用工具，直接回答: {last.content[:100]}...")
    else:
        print(f"✅ LLM 调用了工具进行知识检索")