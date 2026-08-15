"""
dal/dao/teacher_todo_dao.py
教师待办 DAO —— 上课时间到达时自动生成，教师确认消课后自动完成
"""
from __future__ import annotations
from datetime import date, datetime
from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO
from dal.models.teacher_todo_model import TeacherTodo
from dal.models.enums import TodoStatus


class TeacherTodoDao(SqlalchemyBaseDAO):
    """教师每日待办 DAO"""
    primary_key = "id"
    deleted_field = "deleted_at"

    @property
    def model(self):
        return TeacherTodo

    async def create_todo(
        self,
        teacher_id: int,
        schedule_id: int,
        course_id: int,
        student_id: int,
        todo_date: date,
        title: str,
        detail: str | None = None,
    ) -> TeacherTodo:
        """创建待办项——调度器在课程时间到达时自动调用"""
        return await self.create(
            teacher_id=teacher_id,
            schedule_id=schedule_id,
            course_id=course_id,
            student_id=student_id,
            todo_date=todo_date,
            title=title,
            detail=detail,
            status=TodoStatus.PENDING.value,
        )

    async def get_today_todos(self, teacher_id: int) -> list[TeacherTodo]:
        """查教师今日所有待办"""
        today = date.today()
        return await self.find_all(teacher_id=teacher_id, todo_date=today)

    async def get_todos_by_date(
        self, teacher_id: int, todo_date: date
    ) -> list[TeacherTodo]:
        """按日期查教师待办"""
        return await self.find_all(teacher_id=teacher_id, todo_date=todo_date)

    async def mark_done(self, todo_id: int) -> TeacherTodo | None:
        """标记待办已完成——教师确认消课时调用"""
        return await self.update(
            todo_id,
            status=TodoStatus.DONE.value,
            completed_at=datetime.now(),
        )

    async def cancel_todo(self, todo_id: int) -> TeacherTodo | None:
        """取消待办——排课取消/学生请假等场景"""
        return await self.update(todo_id, status=TodoStatus.CANCELLED.value)

    async def todo_exists(self, schedule_id: int, todo_date: date) -> bool:
        """检查某排课当天的待办是否已存在——防重复生成"""
        return await self.exists(schedule_id=schedule_id, todo_date=todo_date)