"""
schemas/pre_schedule_schema.py —— 预排课业务 Schema
==================================================
对应 Service：PreScheduleService
对应数据表：pre_schedule
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PreScheduleResponse(BaseModel):
    """预排课记录响应"""

    id: int = Field(..., description="预排课ID")
    student_id: int = Field(..., description="学生ID")
    student_name: Optional[str] = Field(None, description="学生姓名")
    course_id: int = Field(..., description="课程ID")
    course_name: Optional[str] = Field(None, description="课程名称")
    preferred_time: Optional[str] = Field(None, description="期望上课时间")
    day_of_week: Optional[int] = Field(None, description="期望星期几 1-7")
    start_time: Optional[str] = Field(None, description="期望开始时间 HH:MM")
    end_time: Optional[str] = Field(None, description="期望结束时间 HH:MM")
    preferred_teacher_id: Optional[int] = Field(None, description="期望教师ID")
    preferred_teacher_name: Optional[str] = Field(None, description="期望教师姓名")
    status: str = Field(..., description="审核状态：pending=待审核, approved=通过, rejected=拒绝")
    submit_time: Optional[datetime] = Field(None, description="提交时间")
    reviewer_id: Optional[int] = Field(None, description="审核人ID")
    review_time: Optional[datetime] = Field(None, description="审核时间")
    review_note: Optional[str] = Field(None, description="审核备注")
    created_at: Optional[datetime] = Field(None, description="创建时间")

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, record) -> "PreScheduleResponse":
        """从 SQLAlchemy PreSchedule 模型构建响应"""
        return cls(
            id=record.id,
            student_id=record.student_id,
            student_name=getattr(record.student, "real_name", "") if record.student else "",
            course_id=record.course_id,
            course_name=getattr(record.course, "course_name", "") if record.course else "",
            preferred_time=record.preferred_time,
            day_of_week=record.day_of_week,
            start_time=record.start_time.strftime("%H:%M") if record.start_time else None,
            end_time=record.end_time.strftime("%H:%M") if record.end_time else None,
            preferred_teacher_id=record.preferred_teacher_id,
            preferred_teacher_name=getattr(record.preferred_teacher, "real_name", "") if record.preferred_teacher else "",
            status=record.status.value if hasattr(record.status, "value") else record.status,
            submit_time=record.submit_time,
            reviewer_id=record.reviewer_id,
            review_time=record.review_time,
            review_note=record.review_note,
            created_at=record.created_at,
        )


class PreScheduleListResponse(BaseModel):
    """预排课列表响应"""

    items: list[PreScheduleResponse] = Field(..., description="预排课列表")
    total: int = Field(..., description="总记录数")


class SubmitResponse(BaseModel):
    """提交预排课响应"""

    id: int = Field(..., description="预排课ID")
    student_id: int = Field(..., description="学生ID")
    student_name: str = Field(default="", description="学生姓名")
    course_id: int = Field(..., description="课程ID")
    course_name: str = Field(default="", description="课程名称")
    status: str = Field(..., description="审核状态")
    message: str = Field(default="提交成功，等待老师审核", description="提示信息")


class ReviewResponse(BaseModel):
    """审核预排课响应"""

    pre_schedule_id: int = Field(..., description="预排课ID")
    student_name: str = Field(default="", description="学生姓名")
    course_name: str = Field(default="", description="课程名称")
    teacher_name: str = Field(default="", description="授课教师姓名")
    status: str = Field(..., description="新状态")
    schedule_id: Optional[int] = Field(None, description="审核通过后生成的正式排课ID")
    message: str = Field(..., description="审核结果说明")
