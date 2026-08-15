"""
dal/dao/lesson_consumption_dao.py
课时消耗 DAO —— 消课记录的增删查
"""
from __future__ import annotations
from datetime import datetime, date
from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO
from dal.models.lesson_consumption_model import LessonConsumption
from dal.models.enums import ConsumptionStatus


class LessonConsumptionDao(SqlalchemyBaseDAO):
    """课时消耗记录 DAO"""
    primary_key = "id"
    deleted_field = "deleted_at"

    @property
    def model(self):
        return LessonConsumption

    async def create_consumption(
        self,
        schedule_id: int,
        course_id: int,
        teacher_id: int,
        student_id: int,
        consumed_at: datetime | None = None,
        lesson_index: int | None = None,
    ) -> LessonConsumption:
        """创建消课记录——教师确认消课时调用"""
        return await self.create(
            schedule_id=schedule_id,
            course_id=course_id,
            teacher_id=teacher_id,
            student_id=student_id,
            consumed_at=consumed_at or datetime.now(),
            lesson_index=lesson_index,
            status=ConsumptionStatus.CONFIRMED.value,
        )

    async def get_consumption_by_schedule(
        self, schedule_id: int
    ) -> LessonConsumption | None:
        """查某个排课是否已被消费（不区分学生，只判断排课本身有无消课记录）"""
        return await self.find_one(
            schedule_id=schedule_id, status=ConsumptionStatus.CONFIRMED.value
        )

    async def get_consumption_by_schedule_and_student(
        self, schedule_id: int, student_id: int
    ) -> LessonConsumption | None:
        """查某个排课的某个学生是否已消课（防同一排课+同一学生重复消课）"""
        return await self.find_one(
            schedule_id=schedule_id,
            student_id=student_id,
            status=ConsumptionStatus.CONFIRMED.value,
        )

    async def get_consumptions_by_teacher(
        self, teacher_id: int, skip: int = 0, limit: int = 50
    ) -> list[LessonConsumption]:
        """查某教师的所有消课记录（用于统计教师课消）"""
        return await self.find_all(teacher_id=teacher_id, skip=skip, limit=limit)

    async def get_consumptions_by_student(
        self, student_id: int, skip: int = 0, limit: int = 50
    ) -> list[LessonConsumption]:
        """查某学生的所有消课记录（用于家长查看孩子的课时消耗历史）"""
        return await self.find_all(student_id=student_id, skip=skip, limit=limit)

    async def get_consumptions_by_course(
        self, course_id: int, skip: int = 0, limit: int = 50
    ) -> list[LessonConsumption]:
        """查某课程的所有消课记录"""
        return await self.find_all(course_id=course_id, skip=skip, limit=limit)

    async def count_consumptions_today(self, teacher_id: int) -> int:
        """统计某教师今日消课数（调度器/统计面板用）"""
        records = await self.find_all(teacher_id=teacher_id, limit=500)
        today = date.today()
        return sum(
            1 for r in records
            if r.consumed_at and r.consumed_at.date() == today
            and r.status == ConsumptionStatus.CONFIRMED.value
        )