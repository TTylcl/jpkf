"""
schemas/course_schema.py —— 课程业务 Schema
===========================================
对应 Service：CourseService
对应数据表：course_info
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CourseResponse(BaseModel):
    """课程信息响应 —— @tool 方法的返回值"""

    course_id: int = Field(..., description="课程唯一标识")
    course_code: Optional[str] = Field(None, description="课程编码")
    course_name: str = Field(..., description="课程名称")
    course_type: Optional[str] = Field(None, description="课程类型：REGULAR=正课, TRIAL=体验课, SUMMER=暑假课")
    teacher_id: Optional[int] = Field(None, description="主讲教师ID")
    teacher_name: Optional[str] = Field(None, description="主讲教师姓名")
    description: Optional[str] = Field(None, description="课程描述")
    total_lessons: Optional[int] = Field(None, description="总课时数")
    price: Optional[float] = Field(None, description="课程价格")
    status: Optional[int] = Field(None, description="状态：0=下架，1=上架")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="最后更新时间")

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, course) -> "CourseResponse":
        """从 SQLAlchemy Course 模型构建响应"""
        return cls(
            course_id=course.course_id,
            course_code=course.course_code,
            course_name=course.course_name,
            course_type=course.course_type.value if hasattr(course.course_type, "value") else course.course_type,
            teacher_id=course.teacher_id,
            teacher_name=course.teacher_name,
            description=course.description,
            total_lessons=course.total_lessons,
            price=float(course.price) if course.price else None,
            status=course.status,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )


class CourseListResponse(BaseModel):
    """课程列表分页响应 —— query_courses 的返回值"""

    items: list[CourseResponse] = Field(..., description="课程列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数")