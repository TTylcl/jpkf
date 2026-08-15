""" dal/dao/student_course_dao.py 学生选课DAO —— 纯单表操作 """
from __future__ import annotations

from typing import TYPE_CHECKING

from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO
from dal.models.student_course_model import StudentCourse
from dal.models.enums import StudentCourseStatus

if TYPE_CHECKING:
    from dal.models.student_course_model import StudentCourse as model


class StudentCourseDao(SqlalchemyBaseDAO):
    """学生选课 DAO"""

    @property
    def model(self):
        return StudentCourse

    primary_key = "id"
    deleted_field = "deleted_at"

    # ==================== 单条查询 ====================

    async def get_by_student_and_course(
        self, student_id: int, course_id: int
    ) -> model | None:
        return await self.find_one(student_id=student_id, course_id=course_id)

    # ==================== 多条查询 ====================

    async def get_student_courses(self, student_id: int) -> list[model]:
        """学生所有选课记录（含已退课、已完成）"""
        return await self.find_all(student_id=student_id)

    async def get_student_active_courses(self, student_id: int) -> list[model]:
        """学生已生效的选课"""
        return await self.find_all(
            student_id=student_id,
            status=StudentCourseStatus.ACTIVE.value,  # ← 修：枚举值
        )

    async def list_course_students(self, course_id: int) -> list[model]:
        """课程的所有在读学生"""
        return await self.find_all(
            course_id=course_id,
            status=StudentCourseStatus.ACTIVE.value,
        )

    # ==================== 统计 ====================

    async def count_student_courses(self, student_id: int) -> int:
        """学生已选课程数"""
        return await self.count(
            student_id=student_id,
            status=StudentCourseStatus.ACTIVE.value,
        )

    async def count_course_students(self, course_id: int) -> int:
        """课程在读人数"""
        return await self.count(
            course_id=course_id,
            status=StudentCourseStatus.ACTIVE.value,
        )