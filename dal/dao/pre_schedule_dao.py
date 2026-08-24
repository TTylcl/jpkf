""" dal/dao/pre_schedule_dao.py 预排课数据访问层 —— 纯单表操作 """
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO
from dal.models.enums import PreScheduleStatus

if TYPE_CHECKING:
    from dal.models.pre_schedule_model import PreSchedule as model


class PreScheduleDao(SqlalchemyBaseDAO):
    """预排课 DAO —— 只做单表操作"""

    primary_key = "id"
    deleted_field = "deleted_at"

    @property
    def model(self):
        from dal.models.pre_schedule_model import PreSchedule
        return PreSchedule

    # ==================== 家长提交 ====================

    async def submit(
        self,
        student_id: int,
        course_id: int,
        preferred_time: str | None = None,
        preferred_teacher_id: int | None = None,
        day_of_week: int | None = None,
        start_time=None,
        end_time=None,
    ) -> model:
        """家长提交预排课申请，状态为待审核；结构化时间字段由调用方解析后传入"""
        return await self.create(
            student_id=student_id,
            course_id=course_id,
            preferred_time=preferred_time,
            preferred_teacher_id=preferred_teacher_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            status=PreScheduleStatus.PENDING,
            submit_time=datetime.now(),
        )

    # ==================== 老师审核 ====================

    async def review(
        self,
        pre_schedule_id: int,
        reviewer_id: int,
        status: PreScheduleStatus,
        review_note: str | None = None,
    ) -> model | None:
        """审核预排课：通过/拒绝"""
        return await self.update(
            pre_schedule_id,
            status=status,
            reviewer_id=reviewer_id,
            review_time=datetime.now(),
            review_note=review_note,
        )

    # ==================== 查询 ====================

    async def get_pending_reviews(
        self, skip: int = 0, limit: int = 100
    ) -> list[model]:
        """查询所有待审核的预排课"""
        return await self.find_all(
            skip=skip, limit=limit, status=PreScheduleStatus.PENDING
        )

    async def get_by_student(
        self, student_id: int, skip: int = 0, limit: int = 100
    ) -> list[model]:
        """查询某个学生的所有预排课记录"""
        return await self.find_all(
            skip=skip, limit=limit, student_id=student_id
        )

    async def get_by_id_with_details(self, pre_schedule_id: int) -> model | None:
        """按 ID 查询预排课，同时加载关联的学生、课程、教师"""
        from sqlalchemy.orm import selectinload
        instance = await self.session.get(
            self.model,
            pre_schedule_id,
            options=[
                selectinload(self.model.student),
                selectinload(self.model.course),
                selectinload(self.model.preferred_teacher),
            ],
        )
        if instance is None:
            return None
        if self.deleted_field and getattr(instance,self.deleted_field,None) is not None:
            return None
        return instance