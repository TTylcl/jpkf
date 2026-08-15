"""
schemas/teacher_todo_schema.py —— 教师待办 Schema
==================================================
对应 Service：TeacherTodoService
对应数据表：teacher_todo
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class TodoItem(BaseModel):
    """教师待办项 —— 消课待办 或 待审核预排课"""
    id: int = Field(..., description="待办ID")
    teacher_id: int = Field(..., description="教师ID")
    schedule_id: int = Field(0, description="关联排课ID（预排课审核时为0）")
    course_id: int = Field(..., description="课程ID")
    student_id: int = Field(..., description="学生ID")
    student_name: str = Field("", description="学生姓名")
    todo_date: date | None = Field(None, description="待办日期")
    title: str = Field(..., description="待办标题")
    detail: Optional[str] = Field(None, description="待办详情")
    status: str = Field(..., description="状态：pending/done/cancelled")
    todo_type: str = Field("consumption", description="类型：consumption=消课 / pre_schedule_review=预排课审核")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    created_at: Optional[datetime] = Field(None, description="创建时间")

    model_config = {"from_attributes": True}


class TodoListResponse(BaseModel):
    """教师待办列表响应"""
    items: list[TodoItem] = Field(..., description="待办列表")
    total: int = Field(..., description="总记录数")
