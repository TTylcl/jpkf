import pytest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.context import CTX

from unittest.mock import patch, AsyncMock
from schemas.rag_schemas import RagQuery, RagResult
from core.service.models import ServiceResult
@pytest.fixture
def mock_ctx():
    """最小化上下文，用于权限检查"""
    return CTX(
        user_id=1,
        user_role="admin",
        agent_role="edu_admin_agent",  # 必须，装饰器会校验
        trace_id="test-trace",
        wx_openid="",
        session=None
    )

@pytest.fixture
def rag_service():
    from service.rag_service import RagService
    return RagService()

@pytest.fixture
def rag_query():
    return RagQuery(
        query="退费要多久",
        top_k=5,
        distance_threshold=0.5,
        source_filter=None
    )

@pytest.fixture
def mock_vector_db_results():
    """模拟向量数据库返回"""
    return [
        {
            "chunk_text": "退费需要在开课前7天申请，扣除10%手续费后退还剩余费用。",
            "source": "星弦文化科技有限公司-退费规则.md",
            "chunk_index": 1,
            "distance": 0.15,
        },
        {
            "chunk_text": "开课后不满1/3课时可退50%，超过1/3课时不予退费。",
            "source": "星弦文化科技有限公司-退费规则.md",
            "chunk_index": 2,
            "distance": 0.25,
        },
        {
            "chunk_text": "我们的课程体系包括：钢琴、小提琴、古筝、吉他等乐器课程。",
            "source": "星弦文化科技有限公司-课程体系.md",
            "chunk_index": 1,
            "distance": 0.35,
        },
        {
            "chunk_text": "机构成立于2018年，专注于音乐教育，已有5000+学员。",
            "source": "星弦文化科技有限公司-机构介绍.md",
            "chunk_index": 1,
            "distance": 0.75,   # 会被过滤
        }
    ]




class TestRagService:

    @pytest.mark.asyncio
    async def test_search_basic(self, rag_service, mock_ctx, rag_query, mock_vector_db_results):
        """测试1：基本检索，验证过滤与字段"""
        with patch('service.rag_service.VectorDB') as mock_db:
            mock_db.similarity_search = AsyncMock(return_value=mock_vector_db_results)

            result = await rag_service.search(
                mock_ctx,
                query=rag_query.query,
                top_k=rag_query.top_k,
                distance_threshold=rag_query.distance_threshold,
                source_filter=rag_query.source_filter,
            )

            # 1. 确保返回的是 ServiceResult
            assert isinstance(result, ServiceResult)
            assert result.success is True

            # 2. 取出真正的 RagResult
            rag_result = result.data
            assert isinstance(rag_result, RagResult)

            # 3. 验证数值
            assert rag_result.total_found == 4
            assert rag_result.total_used == 3   # distance=0.75 被过滤
            assert len(rag_result.documents) == 3

            # 4. 验证第一条内容
            first_doc = rag_result.documents[0]
            assert first_doc.chunk_text == "退费需要在开课前7天申请，扣除10%手续费后退还剩余费用。"
            assert first_doc.source == "星弦文化科技有限公司-退费规则.md"
            assert first_doc.chunk_index == 1
            assert first_doc.distance == 0.15

            # 5. context 不为空
            assert "退费需要在开课前" in rag_result.context

    @pytest.mark.asyncio
    async def test_search_empty_result(self, rag_service, mock_ctx):
        """测试2：向量库无返回时，应返回空结果"""
        query = RagQuery(query="不存在的关键字", top_k=3, distance_threshold=0.5)
        with patch('service.rag_service.VectorDB') as mock_db:
            mock_db.similarity_search = AsyncMock(return_value=[])

            result = await rag_service.search(
                mock_ctx,
                query=query.query,
                top_k=query.top_k,
                distance_threshold=query.distance_threshold,
                source_filter=query.source_filter,
            )
            assert result.success
            rag_result = result.data
            assert rag_result.total_found == 0
            assert rag_result.total_used == 0
            assert len(rag_result.documents) == 0
            assert rag_result.context == ""

    @pytest.mark.asyncio
    async def test_search_top_k(self, rag_service, mock_ctx, mock_vector_db_results):
        """测试3：top_k 参数正确传递"""
        query = RagQuery(query="退费", top_k=2, distance_threshold=0.5)

        with patch('service.rag_service.VectorDB') as mock_db:
            # 捕获调用参数
            received_kwargs = {}

            async def capture(**kwargs):
                received_kwargs.update(kwargs)
                # 只返回前两条，模拟 top_k 效果
                return mock_vector_db_results[:2]

            mock_db.similarity_search = AsyncMock(side_effect=capture)

            result = await rag_service.search(
                mock_ctx,
                query=query.query,
                top_k=query.top_k,
                distance_threshold=query.distance_threshold,
                source_filter=query.source_filter,
            )
            assert result.success
            rag_result = result.data
            assert rag_result.total_found == 2
            # 验证 top_k 被正确传入
            assert received_kwargs.get("top_k") == 2

    @pytest.mark.asyncio
    async def test_search_distance_filter(self, rag_service, mock_ctx, mock_vector_db_results):
        """测试4：距离过滤生效"""
        query = RagQuery(query="退费", top_k=5, distance_threshold=0.3)  # 只保留 0.15, 0.25 两条
        with patch('service.rag_service.VectorDB') as mock_db:
            mock_db.similarity_search = AsyncMock(return_value=mock_vector_db_results)

            result = await rag_service.search(
                mock_ctx,
                query=query.query,
                top_k=query.top_k,
                distance_threshold=query.distance_threshold,
                source_filter=query.source_filter,
            )
            assert result.success
            rag_result = result.data
            assert rag_result.total_found == 4
            assert rag_result.total_used == 2
            assert all(doc.distance <= 0.3 for doc in rag_result.documents)

    @pytest.mark.asyncio
    async def test_permission_denied(self, rag_service):
        """测试5：无权限角色应返回失败（需修改 ctx.agent_role）"""
        from core.context import CTX
        bad_ctx = CTX(
            user_id=1,
            user_role="guest",
            agent_role="unknown_role",   # 未授权的角色
            trace_id="test",
            wx_openid="",
            session=None
        )
        query = RagQuery(query="测试", top_k=1, distance_threshold=0.5)
        result = await rag_service.search(
            bad_ctx,
            query=query.query,
            top_k=query.top_k,
            distance_threshold=query.distance_threshold,
            source_filter=query.source_filter,
        )
        assert result.success is False
        assert result.code == 403   # 或你的权限错误码
