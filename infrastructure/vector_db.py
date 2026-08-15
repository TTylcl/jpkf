# infrastructure/vector_db.py

"""
【职责】pgvector 向量检索，复用 AsyncDatabase 连接池
【设计原则】
1. 只负责向量存储和检索，不管业务逻辑
2. 复用 AsyncDatabase 连接池，不自己创建连接
3. 返回原始数据，不做业务处理
【使用方式】
from infrastructure.vector_db import VectorDB
results = await VectorDB.similarity_search("退费要多久", top_k=3)
"""

from typing import Optional
from sqlalchemy import text
from core.database import AsyncDatabase
from infrastructure.embedding import create_embedding

class VectorDB:
    "pgvector 向量数据库操作"
    @staticmethod   # 静态方法
    async def similarity_search(
        query: str,                            # 查询内容          
        top_k: int = 5,                        # 返回结果数量
        source_filter: Optional[str] = None,   # 过滤条件
    ) -> list[dict]:
        """
        余弦相似度检索

        :param query: 用户查询文本
        :param top_k: 返回最相似的k个结果
        :param source_filter: 可选，按来源文件名过滤
        :return: [{chunk_text, source, chunk_index, distance}]
        """
        #1 查询文本向量化
        embedding_model = create_embedding()
        query_vector = embedding_model.embed_query(query)

        #2 向量转字符串 sql::vector转换
        vector_str = "[" + ",".join([str(x) for x in query_vector]) + "]"

        #3 构造sql
        if source_filter:
            sql = text("""
                SELECT chunk_text, source, chunk_index,
                       embedding <=> CAST(:query_vector AS vector) AS distance
                FROM knowledge_chunks
                WHERE source = :source_filter
                ORDER BY embedding <=> CAST(:query_vector AS vector)
                LIMIT :top_k
            """)
            params = {
                "query_vector": vector_str,     # 向量字符串
                "source_filter": source_filter, # 来源文件名
                "top_k": top_k,                 # 返回结果数量
            }
        else:
            sql = text("""
                SELECT chunk_text, source, chunk_index,
                       embedding <=> CAST(:query_vector AS vector) AS distance
                FROM knowledge_chunks
                ORDER BY embedding <=> CAST(:query_vector AS vector)
                LIMIT :top_k
            """)
            params = {"query_vector": vector_str, "top_k": top_k}

        #4 执行sql
        async with AsyncDatabase.get_session() as session:
            results = await session.execute(sql, params)
            rows = results.fetchall()
        #5 返回结果
        return [
            {
                "chunk_text": row[0],
                "source": row[1],
                "chunk_index": row[2],
                "distance": float(row[3]),
            }
            for row in rows
        ]
















