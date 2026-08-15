# test/test_rag_simple.py
"""最简 RAG 测试"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from core.database import AsyncDatabase
from core.graph.builder import build_agent_graph
from core.context import AgentContext
from core import settings
from langchain_core.messages import HumanMessage


async def main():
    AsyncDatabase.init(database_url=settings.DB_URI_TEST)
    graph = build_agent_graph()
    print("✅ Graph 初始化完成")

    ctx = AgentContext(user_id="1", role="admin", agent_role="edu_admin_agent")

    print("\n=== 测试：退费规则 ===")
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="退费规则是什么")]},
        config={"configurable": {"thread_id": "rag-test-1"}},
        context=ctx,
    )
    for m in result["messages"]:
        print(f"[{m.type}] {str(m.content)[:150]}")


if __name__ == "__main__":
    asyncio.run(main())