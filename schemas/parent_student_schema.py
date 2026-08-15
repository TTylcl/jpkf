"""
schemas/parent_student_schema.py —— 家长-学生关联业务 Schema
============================================================
对应 Service：ParentStudentService
对应数据表：parent_student
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ParentStudentResponse(BaseModel):
    """
    家长-学生绑定关系响应 —— @tool 方法的返回值
    """

    id: int = Field(..., description="绑定记录ID")
    parent_id: int = Field(..., description="家长用户ID")
    student_id: int = Field(..., description="学生用户ID")
    relation: str = Field(..., description="关系：father=父亲, mother=母亲, guardian=监护人")
    created_at: Optional[datetime] = Field(None, description="绑定时间")
    updated_at: Optional[datetime] = Field(None, description="最后更新时间")

    model_config = {"from_attributes": True}


    @classmethod
    def from_orm_model(cls, record) -> "ParentStudentResponse":
        """从 SQLAlchemy ParentStudent 模型构建响应"""
        return cls(
            id=record.id,
            parent_id=record.parent_id,
            student_id=record.student_id,
            relation=record.relation,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
class ParentStudentListResponse(BaseModel):
    """绑定关系列表响应"""

    items: list[ParentStudentResponse] = Field(..., description="绑定关系列表")
    total: int = Field(..., description="总记录数")
class UnbindParentStudentResponse(BaseModel):
    """解绑响应"""
    message: str = Field("解绑成功", description="操作结果")