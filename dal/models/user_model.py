"""
dao/models/user_model.py
用户信息表模型
✅ 100%对齐user_info表结构，无任何上层依赖，仅继承SQLAlchemy Base
✅ 兼容SQLAlchemy 2.0异步，自动支持和Course的反向关联teacher_courses
✅ 内置to_dict()方法，直接返回前端可直接用的字典格式
"""
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, SmallInteger, Index
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

from dal.models.base_model import Base # 仅依赖基础模型类
from dal.models.enums import UserType, UserStatus # 仅依赖枚举
from typing import TYPE_CHECKING, List
if TYPE_CHECKING:
    from dal.models.course_model import Course
class User(Base):
    __tablename__ = "user_info"

    # ✅ 覆盖Base的默认id（表主键是user_id，不是默认id），不删除deleted_at（表实际存在该字段）
    id = None

    # ✅ 完全对齐数据库已有的索引+表注释
    __table_args__ = (
        Index("idx_user_info_user_type", "user_type"),
        Index("idx_user_info_status", "status"),
        {"comment": "用户信息表"}
    )

    # ==================== 字段100%对齐表结构，类型/可空/默认值完全匹配 ====================
    user_id: Mapped[int] = mapped_column(
        primary_key=True,
        comment="用户唯一标识，自增主键"
    )
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,  # 默认为NOT NULL
        comment="用户昵称"
    )
    real_name: Mapped[str | None] = mapped_column(
        String(50),
        comment="用户真实姓名"
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        comment="手机号"
    )
    email: Mapped[str | None] = mapped_column(
        String(100),
        comment="电子邮箱"
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        comment="密码hash值"
    )
    user_type: Mapped[UserType] = mapped_column(
        PGEnum(UserType, name="user_type_enum", create_type=False), # 不自动创建枚举，避免冲突
        default=UserType.STUDENT,
        comment="用户类型：STUDENT学生/TEACHER老师/ADMIN管理员/PARENT家长"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=UserStatus.ENABLE.value,
        comment="状态：1=启用，0=禁用"
    )
    # created_at/updated_at/deleted_at 从Base继承，和表字段完全对齐，无需重复定义
    # ==================================================================================

    # ✅ 关联说明：Course模型已经通过backref="teacher_courses"自动给User生成了反向关联
    # 无需在这里显式写relationship，避免导入Course导致循环，直接使用user.teacher_courses即可查老师的授课
    teacher_courses: Mapped[List["Course"]] = relationship(
        back_populates="teacher", # 必须和Course里的关联字段名"teacher"完全一致
        lazy="selectin", # 需要时才加载，避免不必要的性能开销

    )
   
    # ✅ 便捷属性，业务代码直接用
    @property
    def is_enabled(self) -> bool:
        return self.status == UserStatus.ENABLE.value
    @property
    def is_student(self) -> bool:
        return self.user_type == UserType.STUDENT
    @property
    def is_teacher(self) -> bool:
        return self.user_type == UserType.TEACHER
    @property
    def is_admin(self) -> bool:
        return self.user_type == UserType.ADMIN
    @property
    def is_parent(self) -> bool:
        return self.user_type == UserType.PARENT

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, real_name={self.real_name}, type={self.user_type.value})>"