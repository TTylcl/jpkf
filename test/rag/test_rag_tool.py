"""测试 RAG 工具链路：RagService → VectorDB"""
# 最后更新：2026-06-14

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
    AsyncDatabase.init(settings.DB_URI_TEST)

    ctx = CTX(
        user_id=9,
        user_role="parent",
        agent_role="customer_service_agent",
        trace_id="rag-tool-test-uid9",
        wx_openid="wx_test_9",
        session=None,
    )

    service = RagService()

    # 测试1：有哪些课程
    print("=== 测试1：有什么课程 ===")
    result = await service.search(ctx, query="有什么课程", top_k=3)
    if result.success:
        r = result.data
        print(f"命中: {r.total_found}, 使用: {r.total_used}")
        print(f"context:\n{r.context}\n")
    else:
        print(f"失败: {result.message}")

    # 测试2：架子鼓课程
    print("=== 测试2：架子鼓课程 ===")
    result = await service.search(ctx, query="架子鼓课程有哪些", top_k=3)
    if result.success:
        r = result.data
        print(f"命中: {r.total_found}, 使用: {r.total_used}")
        print(f"context:\n{r.context}\n")
    else:
        print(f"失败: {result.message}")

    # 测试3：课程价格
    print("=== 测试3：课程价格 ===")
    result = await service.search(ctx, query="课程多少钱", top_k=3)
    if result.success:
        r = result.data
        print(f"命中: {r.total_found}, 使用: {r.total_used}")
        print(f"context: {r.context}\n")
    else:
        print(f"失败: {result.message}")

    # 测试4：空查询
    print("=== 测试4：空查询 ===")
    result = await service.search(ctx, query="", top_k=3)
    print(f"success={result.success}, message={result.message}")

    await AsyncDatabase.close()


if __name__ == "__main__":
    asyncio.run(main())
