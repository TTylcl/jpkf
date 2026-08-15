"""
tests/dal/query/test_user_query_service.py
UserQueryService 单元测试（Agent 动态查询版）

与 test_course_query_service.py 完全同款写法。

运行方式：
    pytest test/dal/query/test_user_query_service.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from dal.query.user_query_service import UserQueryService, UserFilters
from dal.query import PageResult
from dal.models.user_model import User
from dal.models.enums import UserType


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def query_service(mock_session):
    return UserQueryService(session=mock_session)


@pytest.fixture
def sample_users():
    return [
        _make_user(1, "张老师", "teacher1", UserType.TEACHER, "13800001111",
                   datetime(2024, 6, 1, tzinfo=timezone.utc)),
        _make_user(2, "李老师", "teacher2", UserType.TEACHER, "13800002222",
                   datetime(2024, 8, 15, tzinfo=timezone.utc)),
        _make_user(3, "王同学", "student1", UserType.STUDENT, "13900001111",
                   datetime(2025, 3, 1, tzinfo=timezone.utc)),
        _make_user(4, "赵同学", "student2", UserType.STUDENT, "13900002222",
                   datetime(2025, 9, 10, tzinfo=timezone.utc)),
        _make_user(5, "张三丰", "zhang3", UserType.TEACHER, "13800003333",
                   datetime(2026, 1, 5, tzinfo=timezone.utc)),
        _make_user(6, "刘家长", "parent1", UserType.PARENT, "13700001111",
                   datetime(2026, 4, 20, tzinfo=timezone.utc)),
    ]


def _make_user(user_id, real_name, username, user_type, phone, created_at):
    user = User()
    user.user_id = user_id
    user.real_name = real_name
    user.username = username
    user.user_type = user_type
    user.phone = phone
    user.created_at = created_at
    user.deleted_at = None
    return user


# ============================================================
# UserFilters
# ============================================================

class TestUserFilters:

    def test_default_all_none(self):
        f = UserFilters()
        assert f.keyword is None
        assert f.user_type is None
        assert f.created_after is None
        assert f.created_before is None

    def test_partial_fill(self):
        f = UserFilters(keyword="张", user_type=UserType.TEACHER)
        assert f.keyword == "张"
        assert f.user_type == UserType.TEACHER
        assert f.created_after is None


# ============================================================
# _build_query
# ============================================================

class TestBuildQuery:

    def test_all_empty_filters(self, query_service):
        stmt = query_service._build_query(UserFilters())
        compiled = str(stmt.compile())
        assert "deleted_at" in compiled

    def test_keyword_filter(self, query_service):
        stmt = query_service._build_query(UserFilters(keyword="张"))
        compiled = str(stmt.compile())
        assert "real_name" in compiled
        assert "username" in compiled
        assert "phone" in compiled

    def test_user_type_filter(self, query_service):
        stmt = query_service._build_query(UserFilters(user_type=UserType.TEACHER))
        compiled = stmt.compile()
        assert compiled.params.get("user_type_1") == UserType.TEACHER.value

    def test_time_range_filter(self, query_service):
        after = datetime(2025, 1, 1)
        before = datetime(2026, 1, 1)
        stmt = query_service._build_query(UserFilters(created_after=after, created_before=before))
        compiled = str(stmt.compile())
        assert "created_at" in compiled

    def test_combined_filters(self, query_service):
        f = UserFilters(
            keyword="张",
            user_type=UserType.TEACHER,
            created_after=datetime(2025, 1, 1),
        )
        stmt = query_service._build_query(f)
        compiled = stmt.compile()
        params = compiled.params
        assert params.get("user_type_1") == UserType.TEACHER.value
        # 3 个 keyword 参数 + user_type + created_after
        assert len(params) >= 5


# ============================================================
# query_users
# ============================================================

class TestQueryUsers:

    @pytest.mark.asyncio
    async def test_no_filters_returns_all(self, query_service, mock_session, sample_users):
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(6),
            _make_multi_result(sample_users),
        ]

        result = await query_service.query_users()

        assert isinstance(result, PageResult)
        assert result.total == 6
        assert len(result.items) == 6

    @pytest.mark.asyncio
    async def test_keyword_filter(self, query_service, mock_session, sample_users):
        matched = [u for u in sample_users if "张" in u.real_name]
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(len(matched)),
            _make_multi_result(matched),
        ]

        result = await query_service.query_users(filters=UserFilters(keyword="张"))

        assert result.total == 2  # 张老师, 张三丰

    @pytest.mark.asyncio
    async def test_user_type_filter(self, query_service, mock_session, sample_users):
        matched = [u for u in sample_users if u.user_type == UserType.TEACHER]
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(len(matched)),
            _make_multi_result(matched),
        ]

        result = await query_service.query_users(filters=UserFilters(user_type=UserType.TEACHER))

        assert result.total == 3

    @pytest.mark.asyncio
    async def test_combined_filters(self, query_service, mock_session, sample_users):
        """Agent 组合查询：关键词 + 类型 + 时间"""
        matched = [
            u for u in sample_users
            if u.user_type == UserType.TEACHER
            and u.created_at >= datetime(2025, 1, 1, tzinfo=timezone.utc)
        ]
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(len(matched)),
            _make_multi_result(matched),
        ]

        result = await query_service.query_users(filters=UserFilters(
            user_type=UserType.TEACHER,
            created_after=datetime(2025, 1, 1),
        ))

        assert result.total == 1  # 只有张三丰

    @pytest.mark.asyncio
    async def test_time_range_filter(self, query_service, mock_session, sample_users):
        """最近注册的用户"""
        after = datetime(2026, 1, 1, tzinfo=timezone.utc)
        matched = [u for u in sample_users if u.created_at >= after]
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(len(matched)),
            _make_multi_result(matched),
        ]

        result = await query_service.query_users(filters=UserFilters(created_after=after))

        assert result.total == 2  # 张三丰, 刘家长

    @pytest.mark.asyncio
    async def test_pagination_page2(self, query_service, mock_session, sample_users):
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(6),
            _make_multi_result(sample_users[3:6]),
        ]

        result = await query_service.query_users(page=2, page_size=3)

        assert result.total == 6
        assert result.page == 2
        assert len(result.items) == 3

    @pytest.mark.asyncio
    async def test_ordering(self, query_service, mock_session, sample_users):
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(6),
            _make_multi_result(sample_users),
        ]

        result = await query_service.query_users(order_by="-created_at")

        assert result.total == 6
        data_stmt = mock_session.execute.call_args_list[1][0][0]
        compiled = str(data_stmt.compile())
        assert "DESC" in compiled.upper()

    @pytest.mark.asyncio
    async def test_empty_result(self, query_service, mock_session):
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(0),
            _make_multi_result([]),
        ]

        result = await query_service.query_users(filters=UserFilters(keyword="不存在"))

        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_none_filters_same_as_default(self, query_service, mock_session, sample_users):
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(6),
            _make_multi_result(sample_users),
        ]

        result = await query_service.query_users(filters=None)

        assert result.total == 6


# ============================================================
# count_by_type
# ============================================================

class TestCountByType:

    @pytest.mark.asyncio
    async def test_count_teachers(self, query_service, mock_session):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await query_service.count_by_type(UserType.TEACHER)

        assert count == 3

    @pytest.mark.asyncio
    async def test_count_zero(self, query_service, mock_session):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await query_service.count_by_type(UserType.STUDENT)

        assert count == 0


# ============================================================
# 辅助函数
# ============================================================

def _make_scalar_result(value):
    mock_result = MagicMock()
    mock_result.scalar.return_value = value
    return mock_result


def _make_multi_result(items):
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = items
    mock_result.scalars.return_value = mock_scalars
    return mock_result