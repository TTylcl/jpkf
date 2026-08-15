# service/rag_service.py


"""
【职责】rag 检索
【设计原则】
1 只负责检索业务，不操作数据库

2预留reranker扩展
【使用方式】
from service.rag_service import RagService
result = await RagService().search(ctx, query="退费要多久", top_k=5)
"""
from schemas.rag_schemas import RagDocument,RagResult,RagQuery
from infrastructure.vector_db import VectorDB
from core.service.decorators import tool, ToolMeta
from core.context import CTX
from core.service.models import ServiceResult

class RagService:
    resource = "rag"

    @tool(ToolMeta(
            name="rag_search",
            description="RAG知识库检索工具,机构介绍，课程体系，退费规则，学员评价等信息。",
            parameters={
                "query": {
                    "type": "string",
                    "description": "用户查询文本",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 3,
                },
                "distance_threshold": {
                    "type": "number",
                    "description": "相似度阈值,默认0.5",
                    "default": 0.5,
                },
                "source_filter": {
                    "type": "string",
                    "description": "过滤条件（可选）",
                    "default": None,
                },
            },
            require_permission=True,
    ))
    async def search(
        self,
        ctx: CTX,
        query: str,
        top_k: int = 5,
        distance_threshold: float = 0.7,
        source_filter: str | None = None,
    ) -> ServiceResult:
        """ rag检索 """
        rag_query = RagQuery(
            query=query,
            top_k=top_k,
            distance_threshold=distance_threshold,
            source_filter=source_filter,
        )

        result = await VectorDB.similarity_search(
            query=rag_query.query,
            top_k=rag_query.top_k,
            source_filter=rag_query.source_filter
        )
        total_found = len(result)


        filtered = [
            RagDocument(
                chunk_text=r["chunk_text"],
                source=r["source"],
                chunk_index=r["chunk_index"],
                distance=r["distance"], )
            for r in result if r["distance"] <= rag_query.distance_threshold]
        context = RagService._format_context(filtered)

        return ServiceResult.ok(
            data=RagResult(
                documents=filtered,
                context=context,
                total_found=total_found,
                total_used=len(filtered),
            ),
            trace_id=ctx.trace_id,
        )
    @staticmethod
    def _format_context(documents: list[RagDocument]) -> str:
        """格式化context"""
        if not documents: return ""
        parts = []
        for doc in documents:
            short_source = doc.source.replace("星弦文化科技有限公司", "").strip()
            if short_source.startswith("-") or not short_source:
                short_source = doc.source
            parts.append(f"来源: {short_source}#{doc.chunk_index}]\n{doc.chunk_text}") 
        return "\n\n---\n\n".join(parts)
    # ---------- 扩展点 ----------

    # @staticmethod
    # async def rerank(query: str, documents: list[RagDocument]) -> list[RagDocument]:
    #     raise NotImplementedError("Reranking not implemented yet")




