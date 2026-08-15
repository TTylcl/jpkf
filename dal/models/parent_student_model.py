# dal/models/parent_student_model.py
from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, ForeignKey, String, Boolean, func, text, Index
from sqlalchemy.dialects.postgresql import TIMESTAMP
from dal.models.base_model import Base
from dal.models.enums import ParentRelation

class ParentStudent(Base):
    """家长-学生关联表"""
    __tablename__ = "parent_student"
    __table_args__ = (
        # 完全对齐你现在的唯一约束：同一个家长不能重复绑定同一个学生
        Index(
            "uk_parent_student",
            "parent_id", "student_id",
            unique=True,
            # 如果需要支持解绑后重新绑定，就加下面这行（软删后不算重复）
            # postgresql_where=text("deleted_at IS NULL")
        ),
        Index("idx_parent_id", "parent_id"),
        Index("idx_student_id", "student_id"),
        Index("idx_deleted_at", "deleted_at"),
        {"comment": "家长学生关联表"}
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    parent_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user_info.user_id", ondelete="CASCADE"), nullable=False, comment="家长ID"
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user_info.user_id", ondelete="CASCADE"), nullable=False, comment="学生ID"
    )
    relation: Mapped[str] = mapped_column(
        String(32), default=ParentRelation.GUARDIAN.value, nullable=False, comment="亲属关系"
    )
    
  
    # 通用软删时间字段
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, index=True, nullable=True, comment="删除时间"
    )

    @property
    def is_default_guardian(self) -> bool:
        return self.is_default is True

    def __repr__(self) -> str:
        return f"<ParentStudent(id={self.id}, parent_id={self.parent_id}, student_id={self.student_id}, relation={self.relation})>"