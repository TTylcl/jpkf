"""
RAG 终端输出测试
最后更新：2026-06-14
用法：python test/rag/test_rag_terminal.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from core.database import AsyncDatabase
from core.context import CTX
from service.rag_service import RagService
from core import settings


async def main():
    # 1. 初始化数据库
    print("=" * 60)
    print("🔧 初始化数据库连接...")
    AsyncDatabase.init(database_url=settings.DB_URI_TEST)
    print("✅ 数据库连接初始化完成")

    # 2. 构造 CTX
    ctx = CTX(
        user_id=1,
        user_role="admin",
        agent_role="edu_admin_agent",
        trace_id="rag-terminal-test",
        wx_openid="",
        session=None,  # VectorDB 内部自己开 session
    )

    service = RagService()

    # 3. 多组查询测试
    queries = [
        ("退费规则", "退费规则是什么"),
        ("课程体系", "架子鼓课程有哪些"),
        ("机构介绍", "星弦文化是做什么的"),
    ]

    for label, query in queries:
        print(f"\n{'=' * 60}")
        print(f"🔍 查询：{label}")
        print(f"   问题：{query}")
        print("-" * 60)

        result = await service.search(ctx, query=query, top_k=3, distance_threshold=0.7)

        if result.success:
            rag_result = result.data
            print(f"   命中 {rag_result.total_found} 条，使用 {rag_result.total_used} 条")
            for i, doc in enumerate(rag_result.documents):
                print(f"\n   [{i+1}] 来源：{doc.source} #{doc.chunk_index}")
                print(f"       距离：{doc.distance:.4f}")
                print(f"       内容：{doc.chunk_text[:120]}...")
            if rag_result.context:
                print(f"\n   📝 拼接 context ({len(rag_result.context)} 字符)：")
                print(f"   {'-' * 40}")
                for line in rag_result.context.split("\n")[:10]:
                    print(f"   {line}")
        else:
            print(f"   ❌ 失败：{result.message} (code={result.code})")

    await AsyncDatabase.close()
    print(f"\n{'=' * 60}")
    print("✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
