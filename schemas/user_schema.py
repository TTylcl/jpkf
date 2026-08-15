# \schemas\user_schema.py
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel,Field

class UserResponse(BaseModel):
    user_id: int = Field(..., description="用户唯一标识")
    username: str = Field(..., description="用户昵称")
    real_name: Optional[str] = Field(None, description="真实姓名")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[str] = Field(None, description="电子邮箱")
    user_type: str = Field(..., description="用户类型：STUDENT/TEACHER/ADMIN/PARENT")
    status: int = Field(..., description="状态：1=启用，0=禁用")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="最后更新时间")

    is_enabled: bool = Field(..., description="是否启用")
    is_student: bool = Field(..., description="是否为学生")
    is_teacher: bool = Field(..., description="是否为老师")
    is_admin: bool = Field(..., description="是否为管理员")
    is_parent: bool = Field(..., description="是否为家长")

    model_config = {"from_attributes": True}
    @classmethod
    def from_orm_model(cls, user) -> "UserResponse":
        """从 SQLAlchemy User 模型构建响应"""
        return cls(
            user_id=user.user_id,
            username=user.username,
            real_name=user.real_name,
            phone=user.phone,
            email=user.email,
            user_type=user.user_type.value if hasattr(user.user_type, "value") else user.user_type,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at,
            is_enabled=user.is_enabled,
            is_student=user.is_student,
            is_teacher=user.is_teacher,
            is_admin=user.is_admin,
            is_parent=user.is_parent,
        )
    
class UserCountResponse(BaseModel):
    """用户数量统计响应"""
    user_type: str = Field(..., description="用户类型：STUDENT/TEACHER/ADMIN/PARENT")
    count: int = Field(..., description="该类型用户数量")
    
class UserListResponse(BaseModel):
    """用户列表分页响应"""
    items: list[UserResponse] = Field(..., description="用户列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数")