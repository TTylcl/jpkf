# dal/models/base.py
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有SQLAlchemy模型的基类"""
    
    __abstract__ = True
    
    # 主键ID
    """
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="主键ID"
    )
    """
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="创建时间"
    )
    
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 软删除字段
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="删除时间"
    )
    
    def to_dict(self, exclude: Optional[list] = None) -> dict:
        """
        将模型实例转换为字典
        
        Args:
            exclude: 要排除的字段列表，如 ['password_hash']
            
        Returns:
            dict: 字段名到值的映射
        """
        if exclude is None:
            exclude = []
            
        result = {}
        for column in self.__table__.columns:
            if column.name in exclude:
                continue
                
            value = getattr(self, column.name)
            
            # 处理特殊类型
            if isinstance(value, datetime):
                value = value.isoformat()
            elif hasattr(value, 'value'):  # 处理枚举
                value = value.value
            
            result[column.name] = value
        
        return result
    
    @property
    def is_deleted(self) -> bool:
        """判断是否已删除"""
        return self.deleted_at is not None