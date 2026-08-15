"""tests/dal/query/test_schedule_query_service.py ScheduleQueryService 单元测试"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from dal.query.schedule_query_service import ScheduleQueryService, ScheduleFilters
from dal.query import PageResult



@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def query_service(mock_session):
    return ScheduleQueryService(session=mock_session)


@pytest.fixture
def sample_schedules():
    """周一到周五每天 2 节课，共 10 条（返回 dict，模拟 result.mappings().all()）"""
    schedules = []
    for day in range(1, 6):
        for slot in range(2):
            schedules.append({
                "id": day * 10 + slot,
                "course_id": day * 100,
                "course_name": f"课程{day}",
                "teacher_id": day,
                "teacher_name": f"老师{day}",
                "student_id": 0,
                "student_name": "",
                "day_of_week": day,
                "start_time": "09:00:00",
                "end_time": "10:30:00",
                "classroom": f"教室{day}0{slot+1}",
            })
    return schedules


# ============================================================
# Filters
# ============================================================

class TestScheduleFilters:
    def test_default_all_none(self):
        f = ScheduleFilters()
        assert all(v is None for v in [f.student_id, f.parent_id, f.teacher_id, f.course_id, f.day_of_week])

    def test_partial_fill(self):
        f = ScheduleFilters(teacher_id=5, day_of_week=3)
        assert f.teacher_id == 5 and f.day_of_week == 3


# ============================================================
# BuildQuery
# ============================================================

class TestBuildQuery:
    def test_all_empty_filters(self, query_service):
        stmt = query_service._build_query(ScheduleFilters())
        compiled = str(stmt.compile())
        assert "deleted_at" in compiled

    def test_teacher_id_filter(self, query_service):
        stmt = query_service._build_query(ScheduleFilters(teacher_id=5))
        assert stmt.compile().params.get("teacher_id_1") == 5

    def test_course_id_filter(self, query_service):
        stmt = query_service._build_query(ScheduleFilters(course_id=101))
        assert stmt.compile().params.get("course_id_1") == 101

    def test_day_of_week_filter(self, query_service):
        stmt = query_service._build_query(ScheduleFilters(day_of_week=3))
        assert stmt.compile().params.get("day_of_week_1") == 3

    def test_combined_filters(self, query_service):
        f = ScheduleFilters(teacher_id=3, day_of_week=3)
        params = query_service._build_query(f).compile().params
        assert params.get("teacher_id_1") == 3
        assert params.get("day_of_week_1") == 3


# ============================================================
# QuerySchedules
# ============================================================

class TestQuerySchedules:
    @pytest.mark.asyncio
    async def test_no_filters_returns_all(self, query_service, mock_session, sample_schedules):
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(10),
            _make_multi_result(sample_schedules),
        ]
        result = await query_service.query_schedules()
        assert isinstance(result, PageResult)
        assert result.total == 10
        assert len(result.items) == 10

    @pytest.mark.asyncio
    async def test_teacher_filter(self, query_service, mock_session, sample_schedules):
        matched = [s for s in sample_schedules if s["teacher_id"] == 1]
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(len(matched)),
            _make_multi_result(matched),
        ]
        result = await query_service.query_schedules(filters=ScheduleFilters(teacher_id=1))
        assert result.total == 2  # 周一有 2 节课

    @pytest.mark.asyncio
    async def test_day_of_week_filter(self, query_service, mock_session, sample_schedules):
        matched = [s for s in sample_schedules if s["day_of_week"] == 3]
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(len(matched)),
            _make_multi_result(matched),
        ]
        result = await query_service.query_schedules(filters=ScheduleFilters(day_of_week=3))
        assert result.total == 2

    @pytest.mark.asyncio
    async def test_pagination_page2(self, query_service, mock_session, sample_schedules):
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(10),
            _make_multi_result(sample_schedules[5:10]),  # page 2, 5 items per page
        ]
        result = await query_service.query_schedules(page=2, page_size=5)
        assert result.page == 2
        assert result.total == 10

    @pytest.mark.asyncio
    async def test_empty_result(self, query_service, mock_session):
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            _make_scalar_result(0),
            _make_multi_result([]),
        ]
        result = await query_service.query_schedules(
            filters=ScheduleFilters(teacher_id=999)
        )
        assert result.total == 0
        assert len(result.items) == 0


# ============================================================
# 排序
# ============================================================

class TestOrdering:
    def test_default_ordering(self, query_service):
        stmt = query_service._apply_ordering(
            query_service._build_query(ScheduleFilters()), None
        )
        compiled = str(stmt.compile())
        assert "day_of_week" in compiled
        assert "start_time" in compiled


# ============================================================
# Helpers
# ============================================================

def _make_scalar_result(value):
    r = MagicMock()
    r.scalar.return_value = value
    return r


def _make_multi_result(items):
    """模拟 result.mappings().all() 返回的 RowMapping 列表"""
    r = MagicMock()
    m = MagicMock()
    m.all.return_value = items
    r.mappings.return_value = m
    return r