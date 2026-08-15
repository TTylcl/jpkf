"""
schemas/student_course_schema.py —— 学生选课业务 Schema
======================================================
对应 Service：StudentCourseService
对应数据表：student_courses
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StudentCourseResponse(BaseModel):
    """
    学生选课记录响应 —— @tool 方法的返回值

    家长(get_child_courses)和学生(get_my_courses)共用此 Schema，
    确保两边看到的课程核心信息一致。
    """

    id: int = Field(..., description="选课记录ID")
    student_id: int = Field(..., description="学生ID")
    student_name: Optional[str] = Field(None, description="学生姓名")
    course_id: int = Field(..., description="课程ID")
    course_name: Optional[str] = Field(None, description="课程名称")
    # ── 课程核心字段（与 query_courses 对齐，家长/学生都能看到）──
    course_type: Optional[str] = Field(None, description="课程类型：REGULAR=正课 / TRIAL=体验课 / SUMMER=暑假课")
    teacher_name: Optional[str] = Field(None, description="授课教师姓名")
    price: Optional[float] = Field(None, description="课程单价（元）")
    total_lessons: Optional[int] = Field(None, description="课程总课时数")
    description: Optional[str] = Field(None, description="课程介绍")
    # ── 选课特有字段 ──
    enrolled_at: Optional[datetime] = Field(None, description="选课时间")
    status: str = Field(..., description="选课状态：active=在读, dropped=已退课, completed=已完成")
    purchased_lessons: Optional[int] = Field(None, description="购买课时")
    remaining_lessons: Optional[int] = Field(None, description="剩余课时")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="最后更新时间")

    # 便捷属性
    is_active: bool = Field(..., description="是否在读")

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, record) -> "StudentCourseResponse":
        """从 SQLAlchemy StudentCourse 模型构建响应"""
        course = record.course
        return cls(
            id=record.id,
            student_id=record.student_id,
            student_name=record.student.real_name if record.student else None,
            course_id=record.course_id,
            course_name=course.course_name if course else None,
            # ── 课程核心字段 ──
            course_type=course.course_type.value if course and course.course_type else None,
            teacher_name=course.teacher_name if course else None,
            price=float(course.price) if course and course.price else 0.0,
            total_lessons=course.total_lessons if course else None,
            description=course.description if course else None,
            # ── 选课字段 ──
            enrolled_at=record.enrolled_at,
            status=record.status,
            purchased_lessons=record.purchased_lessons,
            remaining_lessons=record.remaining_lessons,
            created_at=record.created_at,
            updated_at=record.updated_at,
            is_active=record.is_active,
        )


class StudentCourseListResponse(BaseModel):
    """选课记录列表响应"""

    items: list[StudentCourseResponse] = Field(..., description="选课记录列表")
    total: int = Field(..., description="总记录数")


class EnrollResponse(BaseModel):
    """
    报名操作响应 —— enroll_student 的返回值

    统一处理三种场景：新报名、已报名、重新激活
    """

    id: int = Field(..., description="选课记录ID")
    student_id: int = Field(..., description="学生ID")
    student_name: str = Field(default="", description="学生姓名")
    course_id: int = Field(..., description="课程ID")
    course_name: str = Field(default="", description="课程名称")
    status: str = Field(..., description="选课状态：active=在读, dropped=已退课")
    enrolled_at: Optional[str] = Field(None, description="选课时间")
    message: str = Field(..., description="操作结果说明：报名成功 / 学生已报名该课程 / 报名已重新激活")


class EnrollmentCheckResponse(BaseModel):
    """选课状态检查响应 —— check_enrollment 的返回值"""

    enrolled: bool = Field(..., description="是否已选课")