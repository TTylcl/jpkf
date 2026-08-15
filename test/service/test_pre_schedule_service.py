"""
PreScheduleService 集成测试 —— 家长提交 → 老师审核 → 生成正式排课
使用真实数据库 + 事务回滚
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from core.database import AsyncDatabase
from core.context import CTX
from dal.models.user_model import User
from dal.models.course_model import Course
from dal.models.enums import UserType, UserStatus
from service.pre_schedule_service import PreScheduleService

TEST_PARENT_ID = 9101
TEST_STUDENT_ID = 9102
TEST_TEACHER_ID = 9103
TEST_COURSE_ID = 9104

# ===================================================================
# 辅助函数
# ===================================================================


def _ctx(session, agent_role="edu_admin_agent", user_id=999, user_role="admin", trace_id="test") -> CTX:
    return CTX(
        agent_role=agent_role, user_id=user_id, user_role=user_role,
        trace_id=trace_id, wx_openid="", session=session,
    )


async def _insert_user(session, user_id, username, real_name, user_type, phone="13900000001", email="t@t.com"):
    session.add(User(
        user_id=user_id, username=username, real_name=real_name, phone=phone,
        email=email, user_type=user_type, status=UserStatus.ENABLE.value,
    ))
    await session.flush()


async def _insert_course(session, course_id=TEST_COURSE_ID):
    session.add(Course(
        course_id=course_id, course_name="测试课程",
        course_code=f"T{course_id}", teacher_id=TEST_TEACHER_ID,
        teacher_name="测试老师",
    ))
    await session.flush()


async def _insert_users(session):
    await _insert_user(session, TEST_PARENT_ID, "test_parent", "测试家长", UserType.PARENT)
    await _insert_user(session, TEST_STUDENT_ID, "test_student", "测试学生", UserType.STUDENT)
    await _insert_user(session, TEST_TEACHER_ID, "test_teacher", "测试老师", UserType.TEACHER)
    await _insert_course(session)


async def _bind_parent_student(session):
    """绑定家长和学生"""
    from dal.dao.parent_student_dao import ParentStudentDao
    dao = ParentStudentDao(session)
    await dao.bind(TEST_PARENT_ID, TEST_STUDENT_ID, "guardian")


# ===================================================================
# submit_pre_schedule
# ===================================================================


@pytest.mark.asyncio
async def test_submit_pre_schedule_no_binding():
    """未绑定关系时提交应返回 403"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_submit_403")
        service = PreScheduleService()

        result = await service.submit_pre_schedule(
            ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_ID,
            course_id=TEST_COURSE_ID, preferred_time="周一 09:00-10:30",
        )
        assert result.success is False
        assert result.code == 403
        await session.rollback()


@pytest.mark.asyncio
async def test_submit_pre_schedule_success():
    """正常提交预排课"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        await _bind_parent_student(session)
        ctx = _ctx(session, trace_id="test_submit_ok", user_id=TEST_PARENT_ID, user_role="parent")
        service = PreScheduleService()

        result = await service.submit_pre_schedule(
            ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_ID,
            course_id=TEST_COURSE_ID, preferred_time="周三 14:00-15:30",
            preferred_teacher_id=TEST_TEACHER_ID,
        )
        assert result.success is True
        assert result.data.id > 0
        assert result.data.student_id == TEST_STUDENT_ID
        assert result.data.course_id == TEST_COURSE_ID
        assert result.data.status == "pending"  # PENDING
        assert "提交成功" in result.data.message
        await session.rollback()


# ===================================================================
# review_pre_schedule
# ===================================================================


@pytest.mark.asyncio
async def test_review_approve_creates_schedule():
    """审核通过 → 生成正式排课"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        await _bind_parent_student(session)
        ctx = _ctx(session, trace_id="test_approve", user_id=TEST_TEACHER_ID, user_role="teacher")

        # 先提交
        service = PreScheduleService()
        submit = await service.submit_pre_schedule(
            ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_ID,
            course_id=TEST_COURSE_ID,
            preferred_teacher_id=TEST_TEACHER_ID,
        )
        print("==============================================================")
        print(submit.data)
        pre_id = submit.data.id

        # 审核通过
        review = await service.review_pre_schedule(
            ctx=ctx, pre_schedule_id=pre_id, action="approve",
            day_of_week=3, start_time="14:00", end_time="15:30",
            classroom="101",
        )
        assert review.success is True
        assert review.data.status == "approved"  # APPROVED
        assert review.data.schedule_id is not None
        assert review.data.schedule_id > 0
        assert "审核通过" in review.data.message
        await session.rollback()


@pytest.mark.asyncio
async def test_review_reject():
    """审核拒绝"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        await _bind_parent_student(session)
        ctx = _ctx(session, trace_id="test_reject", user_id=TEST_TEACHER_ID, user_role="teacher")

        service = PreScheduleService()
        submit = await service.submit_pre_schedule(
            ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_ID,
            course_id=TEST_COURSE_ID,
        )
        pre_id = submit.data.id

        review = await service.review_pre_schedule(
            ctx=ctx, pre_schedule_id=pre_id, action="reject",
            review_note="时间不合适，请重新选择",
        )
        assert review.success is True
        assert review.data.status == "rejected"  # REJECTED
        assert review.data.schedule_id is None
        assert "已拒绝" in review.data.message
        await session.rollback()


@pytest.mark.asyncio
async def test_review_already_reviewed():
    """重复审核应返回 409"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        await _bind_parent_student(session)
        ctx = _ctx(session, trace_id="test_dup_review", user_id=TEST_TEACHER_ID, user_role="teacher")

        service = PreScheduleService()
        submit = await service.submit_pre_schedule(
            ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_ID,
            course_id=TEST_COURSE_ID,
        )
        pre_id = submit.data.id

        # 第一次审核
        await service.review_pre_schedule(
            ctx=ctx, pre_schedule_id=pre_id, action="reject",
            review_note="已被拒绝",
        )

        # 第二次审核
        review2 = await service.review_pre_schedule(
            ctx=ctx, pre_schedule_id=pre_id, action="approve",
            day_of_week=1, start_time="09:00", end_time="10:00",
        )
        assert review2.success is False
        assert review2.code == 409
        await session.rollback()


@pytest.mark.asyncio
async def test_review_not_found():
    """审核不存在的预排课"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        ctx = _ctx(session, trace_id="test_review_404")

        service = PreScheduleService()
        result = await service.review_pre_schedule(
            ctx=ctx, pre_schedule_id=99999, action="approve",
            day_of_week=1, start_time="09:00", end_time="10:00",
        )
        assert result.success is False
        assert result.code == 404
        await session.rollback()


@pytest.mark.asyncio
async def test_review_approve_missing_time():
    """通过但没有排课参数应返回 400"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        await _bind_parent_student(session)
        ctx = _ctx(session, trace_id="test_missing_time")

        service = PreScheduleService()
        submit = await service.submit_pre_schedule(
            ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_ID,
            course_id=TEST_COURSE_ID,
        )
        pre_id = submit.data.id

        result = await service.review_pre_schedule(
            ctx=ctx, pre_schedule_id=pre_id, action="approve",
        )
        assert result.success is False
        assert result.code == 400
        await session.rollback()


# ===================================================================
# get_pending_reviews
# ===================================================================


@pytest.mark.asyncio
async def test_get_pending_reviews():
    """老师查看待审核列表"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        await _bind_parent_student(session)
        ctx = _ctx(session, trace_id="test_pending", user_id=TEST_TEACHER_ID, user_role="teacher")

        service = PreScheduleService()
        await service.submit_pre_schedule(
            ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_ID,
            course_id=TEST_COURSE_ID,
        )

        result = await service.get_pending_reviews(ctx=ctx)
        assert result.success is True
        assert result.data.total >= 1
        assert len(result.data.items) >= 1
        # 所有记录都应是 PENDING
        for item in result.data.items:
            assert item.status == "pending"
        await session.rollback()


# ===================================================================
# get_my_submissions
# ===================================================================


@pytest.mark.asyncio
async def test_get_my_submissions():
    """家长查看自己的提交记录"""
    async with AsyncDatabase.get_session() as session:
        await _insert_users(session)
        await _bind_parent_student(session)
        ctx = _ctx(session, trace_id="test_my_sub", user_id=TEST_PARENT_ID, user_role="parent")

        service = PreScheduleService()
        await service.submit_pre_schedule(
            ctx=ctx, parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_ID,
            course_id=TEST_COURSE_ID,
        )

        result = await service.get_my_submissions(ctx=ctx, parent_id=TEST_PARENT_ID)
        assert result.success is True
        assert result.data.total >= 1
        assert result.data.items[0].student_id == TEST_STUDENT_ID
        await session.rollback()


@pytest.mark.asyncio
async def test_get_my_submissions_no_bindings():
    """未绑定任何孩子时返回空列表"""
    async with AsyncDatabase.get_session() as session:
        await _insert_user(session, TEST_PARENT_ID, "p", "无孩家长", UserType.PARENT)
        ctx = _ctx(session, trace_id="test_my_sub_empty")

        service = PreScheduleService()
        result = await service.get_my_submissions(ctx=ctx, parent_id=TEST_PARENT_ID)
        assert result.success is True
        assert result.data.total == 0
        await session.rollback()
