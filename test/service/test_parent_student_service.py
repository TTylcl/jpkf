""" ParentStudentService 集成测试 —— 使用真实数据库 + 事务回滚 """
#/test/service/test_parent_student_service.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from core.database import AsyncDatabase
from core.context import CTX
from core import settings
from dal.models.user_model import User
from dal.models.enums import UserType, UserStatus
from service.parent_student_service import ParentStudentService

TEST_PARENT_ID = 9001
TEST_STUDENT_A_ID = 9002
TEST_STUDENT_B_ID = 9003

# ===================================================================
# 辅助函数
# ===================================================================

def _ctx(session, agent_role="edu_admin_agent", trace_id="test") -> CTX:
    return CTX(
        agent_role=agent_role, user_id=999, user_role="admin",
        trace_id=trace_id, wx_openid="", session=session,
    )


async def _insert_user(session, user_id, username, real_name, user_type, phone="13900000001", email="t@t.com"):
    session.add(User(
        user_id=user_id, username=username, real_name=real_name, phone=phone,
        email=email, user_type=user_type, status=UserStatus.ENABLE.value,
    ))
    await session.flush()


async def _insert_users(session):
    """批量插入测试用户"""
    await _insert_user(session, TEST_PARENT_ID, "test_parent", "测试家长", UserType.PARENT)
    await _insert_user(session, TEST_STUDENT_A_ID, "test_stu_a", "测试学生A", UserType.STUDENT)
    await _insert_user(session, TEST_STUDENT_B_ID, "test_stu_b", "测试学生B", UserType.STUDENT)


# ===================================================================
# get_my_children
# ===================================================================

@pytest.mark.asyncio
async def test_get_my_children_empty():
    """未绑定时返回空列表"""
    async with AsyncDatabase.get_session() as session:
        await _insert_user(session, TEST_PARENT_ID, "p", "家长", UserType.PARENT)
        ctx = _ctx(session, trace_id="test_gmc_empty")
        service = ParentStudentService()

        result = await service.get_my_children(ctx=ctx, parent_id=TEST_PARENT_ID)
        assert result.success is True
        assert result.data.total == 0
        assert result.data.items == []

        await session.rollback()


@pytest.mark.asyncio
async def test_get_my_children_with_bindings():
    """绑定后返回正确的学生列表"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_gmc_bind")
        service = ParentStudentService()

        await service.bind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID)
        await service.bind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_B_ID)

        result = await service.get_my_children(ctx=ctx, parent_id=TEST_PARENT_ID)
        assert result.success is True
        assert result.data.total == 2
        ids = {item.student_id for item in result.data.items}
        assert TEST_STUDENT_A_ID in ids
        assert TEST_STUDENT_B_ID in ids

        await session.rollback()


# ===================================================================
# get_student_parents
# ===================================================================

@pytest.mark.asyncio
async def test_get_student_parents_empty():
    """学生未绑定时返回空列表"""
    async with AsyncDatabase.get_session() as session:
        await _insert_user(session, TEST_STUDENT_A_ID, "s", "学生", UserType.STUDENT)
        ctx = _ctx(session, trace_id="test_gsp_empty")
        service = ParentStudentService()

        result = await service.get_student_parents(ctx=ctx, student_id=TEST_STUDENT_A_ID)
        assert result.success is True
        assert result.data.total == 0

        await session.rollback()


@pytest.mark.asyncio
async def test_get_student_parents_with_bindings():
    """绑定后返回正确的家长列表"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_gsp_bind")
        service = ParentStudentService()

        await service.bind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID, relation="mother")

        result = await service.get_student_parents(ctx=ctx, student_id=TEST_STUDENT_A_ID)
        assert result.success is True
        assert result.data.total == 1
        assert result.data.items[0].parent_id == TEST_PARENT_ID
        assert result.data.items[0].relation == "mother"

        await session.rollback()


# ===================================================================
# bind_parent_student
# ===================================================================

@pytest.mark.asyncio
async def test_bind_parent_student():
    """正常绑定家长和学生"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_bind")
        service = ParentStudentService()

        result = await service.bind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID, relation="father")
        assert result.success is True
        assert result.data.parent_id == TEST_PARENT_ID
        assert result.data.student_id == TEST_STUDENT_A_ID
        assert result.data.relation == "father"

        await session.rollback()


@pytest.mark.asyncio
async def test_bind_default_relation():
    """不传 relation 默认为 guardian"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_default_rel")
        service = ParentStudentService()

        result = await service.bind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID)
        assert result.success is True
        assert result.data.relation == "guardian"

        await session.rollback()


@pytest.mark.asyncio
async def test_bind_duplicate_recovers_soft_delete():
    """解绑后再绑定同一组合，恢复原记录并更新 relation"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_dup")
        service = ParentStudentService()

        r1 = await service.bind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID, relation="father")
        first_id = r1.data.id

        await service.unbind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID)

        r2 = await service.bind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID, relation="mother")
        assert r2.data.id == first_id
        assert r2.data.relation == "mother"

        await session.rollback()


# ===================================================================
# unbind_parent_student
# ===================================================================

@pytest.mark.asyncio
async def test_unbind_parent_student():
    """正常解绑"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_unbind")
        service = ParentStudentService()

        await service.bind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID)
        result = await service.unbind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID)
        assert result.success is True

        # 确认已解绑
        children = await service.get_my_children(ctx=ctx, parent_id=TEST_PARENT_ID)
        assert children.data.total == 0

        await session.rollback()


@pytest.mark.asyncio
async def test_unbind_nonexistent():
    """解绑不存在的关系返回错误"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_unbind_404")
        service = ParentStudentService()

        result = await service.unbind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID)
        assert result.success is False
        assert result.code == 400

        await session.rollback()


# ===================================================================
# get_child_courses
# ===================================================================

@pytest.mark.asyncio
async def test_get_child_courses_no_binding():
    """未绑定的家长查课返回 403"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_gcc_403")
        service = ParentStudentService()

        result = await service.get_child_courses(ctx=ctx, parent_id=TEST_PARENT_ID, child_id=TEST_STUDENT_A_ID)
        assert result.success is False
        assert result.code == 403

        await session.rollback()


@pytest.mark.asyncio
async def test_get_child_courses_with_binding():
    """绑定后家长可查孩子选课列表"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_gcc")
        service = ParentStudentService()

        await service.bind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID)

        result = await service.get_child_courses(ctx=ctx, parent_id=TEST_PARENT_ID, child_id=TEST_STUDENT_A_ID)
        assert result.success is True
        assert hasattr(result.data, "items")
        assert hasattr(result.data, "total")

        await session.rollback()


# ===================================================================
# get_child_schedules
# ===================================================================

@pytest.mark.asyncio
async def test_get_child_schedules_no_binding():
    """未绑定的家长查排课返回 403"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_gcs_403")
        service = ParentStudentService()

        result = await service.get_child_schedules(ctx=ctx, parent_id=TEST_PARENT_ID, child_id=TEST_STUDENT_A_ID)
        assert result.success is False
        assert result.code == 403

        await session.rollback()


@pytest.mark.asyncio
async def test_get_child_schedules_with_binding():
    """绑定后家长可查孩子排课"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_gcs")
        service = ParentStudentService()

        await service.bind_parent_student(ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_A_ID)

        result = await service.get_child_schedules(ctx=ctx, parent_id=TEST_PARENT_ID, child_id=TEST_STUDENT_A_ID)
        assert result.success is True
        assert hasattr(result.data, "items")

        await session.rollback()
