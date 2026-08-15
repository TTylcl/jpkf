""" dal/dao/schedule_dao.py 课程排课DAO """
from __future__ import annotations

from datetime import datetime, time
from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dal.models.schedule_model import Schedule as model


class ScheduleDao(SqlalchemyBaseDAO):
    """课程排课DAO"""
    primary_key = "id"
    deleted_field = "deleted_at"

    @property
    def model(self):
        from dal.models.schedule_model import Schedule
        return Schedule
    @staticmethod
    def _convert_time(time_str: str | time) -> time:
        """字符串时间转time对象，兼容asyncpg驱动"""
        if isinstance(time_str, time):
            return time_str
        return datetime.strptime(time_str, "%H:%M").time()
    # ==================== 全用基类封装方法，零原生SQL ====================
    async def get_course_schedules(self, course_id: int) -> list[model]:
        """查询指定课程的所有排课（排除已删除的）"""
        return await self.find_all(course_id=course_id)

    async def get_teacher_schedules(self, teacher_id: int) -> list[model]:
        """查询指定老师的所有排课（排除已删除的）"""
        return await self.find_all(teacher_id=teacher_id)

    async def get_day_schedules(self, day_of_week: int) -> list[model]:
        """查询周几的所有排课（排除已删除的）"""
        return await self.find_all(day_of_week=day_of_week)

    async def check_time_conflict(
        self,
        teacher_id: int,
        day_of_week: int,
        start_time: str,
        exclude_schedule_id: int | None = None
    ) -> bool:
        """检查老师在指定周几的时间是否有排课冲突"""
        # 转换传入的时间为time对象
        check_start = self._convert_time(start_time)
        
        # 先查同老师同天的排课
        schedules = await self.find_all(teacher_id=teacher_id, day_of_week=day_of_week)
        for s in schedules:
            # 排除要更新的自己
            if exclude_schedule_id and s.id == exclude_schedule_id:
                continue
            # 时间重叠判断（现在都是time对象，可以直接比较）
            if not (check_start >= s.end_time or check_start < s.start_time):
                return True
        return False

    async def create_schedule(
        self,
        course_id: int,
        teacher_id: int,
        day_of_week: int,
        start_time: str,
        end_time: str,
        classroom: str | None = None,
        status: int = 1
    ) -> model:
        """新增排课"""
        return await self.create(
            course_id=course_id,
            teacher_id=teacher_id,
            day_of_week=day_of_week,
            start_time=self._convert_time(start_time),
            end_time=self._convert_time(end_time),
            classroom=classroom,
            status=status
        )

    async def update_schedule(self, schedule_id: int, **update_data) -> model | None:
        """更新排课信息"""
        if "start_time" in update_data:
            update_data["start_time"] = self._convert_time(update_data["start_time"])
        if "end_time" in update_data:
            update_data["end_time"] = self._convert_time(update_data["end_time"])
        
        return await self.update(schedule_id, **update_data)
    async def delete_schedule(self, schedule_id: int) -> bool:
        """软删排课"""
        return await self.soft_delete(schedule_id)

    async def schedule_exists(self, schedule_id: int) -> bool:
        """检查排课是否存在（排除已删除的）"""
        return await self.exists(id=schedule_id)