"""
schemas/lesson_consumption_schema.py —— 消课业务 Schema
====================================================
对应 Service：LessonConsumptionService
对应数据表：lesson_consumption
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ConsumeResponse(BaseModel):
    """
    消课操作响应 —— consume_lesson 方法的返回值
    包含消课结果 + 剩余课时，前端可直接展示
    """
    id: int = Field(..., description="消课记录ID")
    schedule_id: int = Field(..., description="排课ID")
    course_id: int = Field(..., description="课程ID")
    course_name: Optional[str] = Field(None, description="课程名称")
    teacher_id: int = Field(..., description="执行消课的教师ID")
    teacher_name: Optional[str] = Field(None, description="教师姓名")
    student_id: int = Field(..., description="学生ID")
    student_name: Optional[str] = Field(None, description="学生姓名")
    consumed_at: str = Field(..., description="消课时间（ISO格式）")
    remaining_lessons: int = Field(..., description="消课后剩余课时（已扣减）")
    message: str = Field(..., description="操作结果说明")


class ConsumptionListItem(BaseModel):
    """消课记录列表项 —— 查询消课历史时返回"""
    id: int = Field(..., description="消课记录ID")
    schedule_id: int = Field(..., description="排课ID")
    course_id: int = Field(..., description="课程ID")
    course_name: Optional[str] = Field(None, description="课程名称")
    teacher_id: int = Field(..., description="教师ID")
    teacher_name: Optional[str] = Field(None, description="教师姓名")
    student_id: int = Field(..., description="学生ID")
    student_name: Optional[str] = Field(None, description="学生姓名")
    consumed_at: Optional[datetime] = Field(None, description="消课时间")
    lesson_index: Optional[int] = Field(None, description="第几课时")
    status: str = Field(..., description="状态：confirmed=已确认 / cancelled=已取消")
    created_at: Optional[datetime] = Field(None, description="记录创建时间")

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, record) -> "ConsumptionListItem":
        """从 SQLAlchemy LessonConsumption 模型构建列表项"""
        return cls(
            id=record.id,
            schedule_id=record.schedule_id,
            course_id=record.course_id,
            course_name=record.course.course_name if record.course else None,
            teacher_id=record.teacher_id,
            teacher_name=record.teacher.real_name if record.teacher else None,
            student_id=record.student_id,
            student_name=record.student.real_name if record.student else None,
            consumed_at=record.consumed_at,
            lesson_index=record.lesson_index,
            status=record.status,
            created_at=record.created_at,
        )


class ConsumptionListResponse(BaseModel):
    """消课记录列表响应"""
    items: list[ConsumptionListItem] = Field(..., description="消课记录列表")
    total: int = Field(..., description="总记录数")