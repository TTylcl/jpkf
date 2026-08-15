# \test\rag\test_vector.py
"""测试向量检索"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from core.database import AsyncDatabase
from infrastructure.vector_db import VectorDB
from core import settings





async def main():
    AsyncDatabase.init(settings.DB_URI_TEST)
    results = await VectorDB.similarity_search("退费要多久", top_k=3)
    for r in results:
        print(f"[distance={r['distance']:.4f}] {r['source']} #{r['chunk_index']}")
        print(f"  {r['chunk_text'][:100]}...")
        print()

if __name__ == "__main__":
    asyncio.run(main())