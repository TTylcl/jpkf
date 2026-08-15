"""
调试脚本：用 admin 身份问"今天有多少个学生上课"
观察 LLM 调了什么工具、返回什么数据
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from core.graph.builder import build_agent_graph
from core.database import AsyncDatabase
from core.context import AgentContext
from core import settings
from langchain_core.messages import HumanMessage


async def main():
    AsyncDatabase.init(database_url=settings.DB_URI_TEST)
    graph = build_agent_graph()

    # admin 身份
    ctx = AgentContext(
        user_id="1",
        user_role="admin",
        agent_role="edu_admin_agent",
    )

    test_queries = [
        "今天有多少个学生上课",
        "有多少个学生上课",
    ]

    for i, query in enumerate(test_queries):
        print("\n" + "=" * 70)
        print(f"📋 测试 {i+1}: {query}")
        print("=" * 70)

        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=query)]},
            config={"agent_role": "edu_admin_agent","trace_id":f"debug-{i}"},
            context=ctx,
        )

        print(f"\n📌 intent: {result.get('intent', 'N/A')}")
        print(f"📌 permission_denied: {result.get('permission_denied', 'N/A')}")
        print(f"\n📩 消息列表 ({len(result['messages'])} 条):")
        for j, m in enumerate(result["messages"]):
            msg_type = m.type
            content_preview = ""
            if hasattr(m, "content") and m.content:
                content_preview = str(m.content)[:200]
            tool_calls_info = ""
            if hasattr(m, "tool_calls") and m.tool_calls:
                tool_calls_info = str([tc.get("name", "?") for tc in m.tool_calls])
            print(f"  [{j}] {msg_type}: {content_preview}{tool_calls_info}")

        # 检查是否调用了工具
        tool_messages = [m for m in result["messages"] if m.type == "tool"]
        ai_messages = [m for m in result["messages"] if m.type == "ai"]
        print(f"\n📊 统计: tool消息={len(tool_messages)}, AI消息={len(ai_messages)}")
        if tool_messages:
            for tm in tool_messages:
                print(f"  🔧 tool name={tm.name}, content={str(tm.content)[:200]}")

    await AsyncDatabase.close()


if __name__ == "__main__":
    asyncio.run(main())
