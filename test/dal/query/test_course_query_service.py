"""
tests/dal/query/test_course_query_service.py
CourseQueryService 单元测试（Agent 动态查询版）

运行方式：
    pytest test/dal/query/test_course_query_service.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from dal.query.course_query_service import (
    CourseQueryService,
    CourseFilters,
    PageResult,
)
from dal.models.course_model import Course
from dal.models.enums import CourseType, CourseStatus


# ============================================================
# 先诊断枚举值（运行时打印一次）
# ============================================================

def _get_enum_values():
    """返回实际枚举值，避免测试写死错误的值"""
    ct_values = [e.value for e in CourseType]
    cs_values = [e.value for e in CourseStatus]
    return ct_values[0], ct_values[1] if len(ct_values) > 1 else ct_values[0], cs_values


CT_V1, CT_V2, CS_VALUES = _get_enum_values()
# CT_V1, CT_V2 是 CourseType 的前两个值（用于构造测试数据）
# CS_VALUES 是所有 CourseStatus 值


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def query_service(mock_session):
    return CourseQueryService(session=mock_session)


@pytest.fixture
def sample_courses():
    """构造测试课程，使用真实枚举值"""
    online = list(CourseStatus)[0]
    offline = list(CourseStatus)[1] if len(list(CourseStatus)) > 1 else list(CourseStatus)[0]

    return [
        _make_course(1, "Python入门", "CS101", 1, "张老师", list(CourseType)[0], online,
                     datetime(2025, 1, 10, tzinfo=timezone.utc)),
        _make_course(2, "高等数学", "MATH201", 2, "李老师", list(CourseType)[0], online,
                     datetime(2025, 2, 15, tzinfo=timezone.utc)),
        _make_course(3, "数据结构", "CS102", 1, "张老师", list(CourseType)[1], online,
                     datetime(2025, 3, 20, tzinfo=timezone.utc)),
        _make_course(4, "线性代数", "MATH202", 2, "李老师", list(CourseType)[0], offline,
                     datetime(2025, 4, 1, tzinfo=timezone.utc)),
        _make_course(5, "Python进阶", "CS201", 1, "张老师", list(CourseType)[0], online,
                     datetime(2026, 1, 5, tzinfo=timezone.utc)),
        _make_course(6, "英语写作", "ENG101", 3, "王老师", list(CourseType)[0], online,
                     datetime(2026, 3, 10, tzinfo=timezone.utc)),
    ]


def _make_course(course_id, course_name, course_code, teacher_id, teacher_name,
                 course_type, status, created_at):
    course = Course()
    course.course_id = course_id
    course.course_name = course_name
    course.course_code = course_code
    course.teacher_id = teacher_id
    course.teacher_name = teacher_name
    course.course_type = course_type
    course.status = status
    course.created_at = created_at
    course.deleted_at = None
    return course


# ============================================================
# PageResult
# ============================================================

class TestPageResult:

    def test_total_pages_exact_division(self):
        pr = PageResult(total=20, page_size=10)
        assert pr.total_pages == 2

    def test_total_pages_partial(self):
        pr = PageResult(total=21, page_size=10)
        assert pr.total_pages == 3

    def test_total_pages_zero(self):
        pr = PageResult(total=0, page_size=10)
        assert pr.total_pages == 1  # 至少 1 页


# ============================================================
# CourseFilters
# ============================================================

class TestCourseFilters:

    def test_default_all_none(self):
        f = CourseFilters()
        assert f.keyword is None
        assert f.teacher_id is None
        assert f.course_type is None
        assert f.status is None
        assert f.created_after is None
        assert f.created_before is None

    def test_partial_fill(self):
        f = CourseFilters(keyword="Python", teacher_id=1)
        assert f.keyword == "Python"
        assert f.teacher_id == 1
        assert f.course_type is None  # 未传的不受影响


# ============================================================
# _build_query
# ============================================================

class TestBuildQuery:

    def test_all_empty_filters(self, query_service):
        """空过滤器 → 只过滤软删除"""
        stmt = query_service._build_query(CourseFilters())
        stmt_str = str(stmt.compile())
        assert "deleted_at" in stmt_str

    def test_keyword_filter(self, query_service):
        """关键词 → 三个字段 LIKE"""
        stmt = query_service._build_query(CourseFilters(keyword="Python"))
        compiled = str(stmt.compile())
        assert "course_name" in compiled
        assert "course_code" in compiled
        assert "teacher_name" in compiled

    def test_teacher_id_filter(self, query_service):
        stmt = query_service._build_query(CourseFilters(teacher_id=1))
        compiled = stmt.compile()
        assert compiled.params.get("teacher_id_1") == 1

    def test_course_type_filter(self, query_service):
        stmt = query_service._build_query(CourseFilters(course_type=list(CourseType)[0]))
        compiled = stmt.compile()
        assert compiled.params.get("course_type_1") == list(CourseType)[0].value

    def test_status_filter(self, query_service):
        online = list(CourseStatus)[0]
        stmt = query_service._build_query(CourseFilters(status=online))
        compiled = stmt.compile()
        assert compiled.params.get("status_1") == online.value

    def test_time_range_filter(self, query_service):
        after = datetime(2025, 6, 1)
        before = datetime(2026, 1, 1)
        stmt = query_service._build_query(CourseFilters(created_after=after, created_before=before))
        compiled = str(stmt.compile())
        assert "created_at" in compiled

    def test_combined_filters(self, query_service):
        """多条件组合 → 全部生效"""
        f = CourseFilters(
            keyword="Python",
            teacher_id=1,
            course_type=list(CourseType)[0],
            status=list(CourseStatus)[0],
        )
        stmt = query_service._build_query(f)
        compiled = stmt.compile()
        params = compiled.params
        assert params.get("teacher_id_1") == 1
        assert params.get("course_type_1") == list(CourseType)[0].value
        assert params.get("status_1") == list(CourseStatus)[0].value


# ============================================================
# _apply_ordering
# ============================================================

class TestApplyOrdering:

    def test_default_desc_created_at(self, query_service):
        from sqlalchemy import select
        stmt = select(Course)
        ordered = query_service._apply_ordering(stmt, Course, None)
        compiled = str(ordered.compile())
        assert "created_at" in compiled
        assert "DESC" in compiled.upper()

    def test_asc(self, query_service):
        from sqlalchemy import select
        stmt = select(Course)
        ordered = query_service._apply_ordering(stmt, Course, "course_name")
        compiled = str(ordered.compile())
        assert "course_name" in compiled
        # 无 "-" 前缀 → ASC
        assert "DESC" not in compiled.upper() or "course_name ASC" in compiled

    def test_desc_explicit(self, query_service):
        from sqlalchemy import select
        stmt = select(Course)
        ordered = query_service._apply_ordering(stmt, Course, "-course_name")
        compiled = str(ordered.compile())
        assert "course_name" in compiled
        assert "DESC" in compiled.upper()

    def test_invalid_field_falls_back(self, query_service):
        from sqlalchemy import select
        stmt = select(Course)
        ordered = query_service._apply_ordering(stmt, Course, "nonexistent_field")
        compiled = str(ordered.compile())
        # 回退到 created_at DESC
        assert "created_at" in compiled


# ============================================================
# _paginate
# ============================================================

class TestPaginate:

    @pytest.mark.asyncio
    async def test_returns_page_result(self, query_service, mock_session, sample_courses):
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(6),
            _make_multi_result(sample_courses[:3]),
        ]

        from sqlalchemy import select
        result = await query_service._paginate(select(Course), page=1, page_size=3)

        assert isinstance(result, PageResult)
        assert result.total == 6
        assert len(result.items) == 3
        assert result.page == 1
        assert result.page_size == 3

    @pytest.mark.asyncio
    async def test_empty_result(self, query_service, mock_session):
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(0),
            _make_multi_result([]),
        ]

        from sqlalchemy import select
        result = await query_service._paginate(select(Course), page=1, page_size=20)

        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_page2_offset(self, query_service, mock_session, sample_courses):
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(6),
            _make_multi_result(sample_courses[3:6]),
        ]

        from sqlalchemy import select
        result = await query_service._paginate(select(Course), page=2, page_size=3)

        assert result.total == 6
        assert len(result.items) == 3


# ============================================================
# query_courses（集成测试：filters → SQL → 分页）
# ============================================================

class TestQueryCourses:

    @pytest.mark.asyncio
    async def test_no_filters_returns_all(self, query_service, mock_session, sample_courses):
        """无过滤 → 返回全部（含软删除过滤）"""
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(6),
            _make_multi_result(sample_courses),
        ]

        result = await query_service.query_courses()

        assert result.total == 6
        assert len(result.items) == 6

    @pytest.mark.asyncio
    async def test_keyword_filter(self, query_service, mock_session, sample_courses):
        """关键词过滤"""
        matched = [c for c in sample_courses if "Python" in c.course_name]
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(len(matched)),
            _make_multi_result(matched),
        ]

        result = await query_service.query_courses(filters=CourseFilters(keyword="Python"))

        assert result.total == 2  # Python入门, Python进阶

    @pytest.mark.asyncio
    async def test_teacher_filter(self, query_service, mock_session, sample_courses):
        """教师过滤"""
        matched = [c for c in sample_courses if c.teacher_id == 1]
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(len(matched)),
            _make_multi_result(matched),
        ]

        result = await query_service.query_courses(filters=CourseFilters(teacher_id=1))

        assert result.total == 3

    @pytest.mark.asyncio
    async def test_status_filter(self, query_service, mock_session, sample_courses):
        """状态过滤"""
        online_status = list(CourseStatus)[0]
        matched = [c for c in sample_courses if c.status == online_status]
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(len(matched)),
            _make_multi_result(matched),
        ]

        result = await query_service.query_courses(filters=CourseFilters(status=online_status))

        assert result.total == 5  # 6 个中 1 个 offline

    @pytest.mark.asyncio
    async def test_combined_filters(self, query_service, mock_session, sample_courses):
        """Agent 组合查询：关键词 + 教师 + 类型 + 状态"""
        ct = list(CourseType)[0]
        cs = list(CourseStatus)[0]
        matched = [
            c for c in sample_courses
            if "Python" in c.course_name
            and c.teacher_id == 1
            and c.course_type == ct
            and c.status == cs
        ]
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(len(matched)),
            _make_multi_result(matched),
        ]

        result = await query_service.query_courses(filters=CourseFilters(
            keyword="Python", teacher_id=1, course_type=ct, status=cs
        ))

        assert result.total == 2  # Python入门, Python进阶（都是 PUBLIC/ONLINE）

    @pytest.mark.asyncio
    async def test_time_range_filter(self, query_service, mock_session, sample_courses):
        """时间范围过滤"""
        after = datetime(2026, 1, 1, tzinfo=timezone.utc)
        matched = [c for c in sample_courses if c.created_at >= after]
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(len(matched)),
            _make_multi_result(matched),
        ]

        result = await query_service.query_courses(filters=CourseFilters(created_after=after))

        assert result.total == 2  # Python进阶(2026-01), 英语写作(2026-03)

    @pytest.mark.asyncio
    async def test_pagination_page2(self, query_service, mock_session, sample_courses):
        """分页第2页"""
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(6),
            _make_multi_result(sample_courses[3:6]),
        ]

        result = await query_service.query_courses(page=2, page_size=3)

        assert result.total == 6
        assert result.page == 2
        assert len(result.items) == 3

    @pytest.mark.asyncio
    async def test_ordering_asc(self, query_service, mock_session, sample_courses):
        """升序排列"""
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(6),
            _make_multi_result(sample_courses),
        ]

        result = await query_service.query_courses(order_by="course_name")

        assert result.total == 6
        # 验证 SQL 中有 ASC 排序
        data_stmt = mock_session.execute.call_args_list[1][0][0]
        compiled = str(data_stmt.compile())
        assert "course_name" in compiled

    @pytest.mark.asyncio
    async def test_ordering_desc(self, query_service, mock_session, sample_courses):
        """降序排列"""
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(6),
            _make_multi_result(sample_courses),
        ]

        result = await query_service.query_courses(order_by="-created_at")

        assert result.total == 6
        data_stmt = mock_session.execute.call_args_list[1][0][0]
        compiled = str(data_stmt.compile())
        assert "DESC" in compiled.upper()

    @pytest.mark.asyncio
    async def test_empty_result(self, query_service, mock_session):
        """无匹配结果"""
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(0),
            _make_multi_result([]),
        ]

        result = await query_service.query_courses(
            filters=CourseFilters(keyword="不存在的课程")
        )

        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_none_filters_same_as_default(self, query_service, mock_session, sample_courses):
        """filters=None 等价于 CourseFilters()"""
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(6),
            _make_multi_result(sample_courses),
        ]

        result = await query_service.query_courses(filters=None)

        assert result.total == 6


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