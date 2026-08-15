"""
dal/dao/student_schedule_dao.py
学生-排课关联 DAO —— 查询某节课分配了哪些学生
"""
from __future__ import annotations

from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO
from dal.models.student_schedule_model import StudentSchedule


class StudentScheduleDao(SqlalchemyBaseDAO):
    """学生排课关联 DAO"""

    @property
    def model(self):
        return StudentSchedule

    primary_key = "id"
    deleted_field = "deleted_at"

    async def get_schedule_students(self, schedule_id: int) -> list[StudentSchedule]:
        """查询某节课分配了哪些学生（含 student 关联，预加载学生信息）"""
        return await self.find_all(schedule_id=schedule_id)
