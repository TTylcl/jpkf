""" dal/dao/course_dao.py """
from __future__ import annotations
from typing import TYPE_CHECKING

from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO
from dal.models.enums import CourseType, CourseStatus

if TYPE_CHECKING:
    from dal.models.course_model import Course as model


class CourseDao(SqlalchemyBaseDAO):

    @property
    def model(self):
        from dal.models.course_model import Course
        return Course

    primary_key = "course_id"
    deleted_field = "deleted_at"

    async def get_by_course_code(self, course_code: str) -> model | None:
        return await self.find_one(course_code=course_code)

    async def exists_by_course_code(self, course_code: str) -> bool:
        return await self.exists(course_code=course_code)