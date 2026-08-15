from typing import Optional, TYPE_CHECKING # 新增导入TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Numeric, SmallInteger, Integer, Text, Index, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from dal.models.base_model import Base
from dal.models.enums import CourseType

# 条件导入：只有静态类型检查时才导入User，运行时不导入，完全避免循环导入
if TYPE_CHECKING:
    from dal.models.user_model import User # 改成你User模型的实际导入路径

class Course(Base):
    __tablename__ = "course_info"

    # ✅ 只覆盖Base的默认id，因为表主键是course_id，不覆盖deleted_at（表实际有该字段）
    id = None

    # ✅ 严格对齐你查的索引+表注释
    __table_args__ = (
        Index("idx_course_info_teacher_id", "teacher_id"),
        Index("idx_course_info_status", "status"),
        {"comment": "课程基础信息表"}
    )

    # ==================== 100%对齐你查的表字段，字段名/类型/可空/默认值完全一致 ====================
    course_id: Mapped[int] = mapped_column(
        Integer, # 对应PG bigint，Python int兼容
        primary_key=True,
        comment="课程唯一标识"
    )
    course_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="课程编码"
    )
    course_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="课程名称"
    )
    course_type: Mapped[Optional[CourseType]] = mapped_column(
        PGEnum(CourseType, name="course_type_enum", create_type=False),
        default=CourseType.REGULAR,
        comment="课程类型：REGULAR=正课, TRIAL=体验课, SUMMER=暑假课"
    )
    teacher_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user_info.user_id", ondelete="NO ACTION", name="fk_course_teacher"),
        comment="主讲教师ID，关联user_info.user_id"
    )
    teacher_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="主讲教师姓名（冗余字段）"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="课程描述"
    )
    total_lessons: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="总课时数"
    )
    price: Mapped[Optional[float]] = mapped_column(
        Numeric(10,2),
        default=0.00,
        comment="课程价格"
    )
    status: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        default=1,
        comment="状态：0-下架，1-上架"
    )
    # created_at/updated_at/deleted_at 从Base继承，和表字段完全对齐，不用重复写
    # ==================================================================================

    # ✅ 关联老师，和你查的外键规则完全一致，自动给User生成teacher_courses反向关联
    teacher: Mapped[Optional["User"]] = relationship(
        back_populates="teacher_courses", # 必须是"teacher_courses"，不能少s、不能写错
        foreign_keys=[teacher_id],
        lazy="selectin"
    )

    # ✅ 便捷转字典方法，直接返回给前端
    def to_dict(self, include_teacher: bool = False) -> dict:
        data = {
            "course_id": self.course_id,
            "course_code": self.course_code,
            "course_name": self.course_name,
            "course_type": self.course_type.value if self.course_type else None,
            "course_type_label": self.course_type.label if self.course_type else None,
            "teacher_id": self.teacher_id,
            "teacher_name": self.teacher_name,
            "description": self.description,
            "total_lessons": self.total_lessons,
            "price": float(self.price) if self.price else 0.00,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None
        }
        #if include_teacher and self.teacher:
        #    data["teacher_info"] = {
        #        "user_id": self.teacher.user_id,
        #        "real_name": self.teacher.real_name,
        #        "phone": self.teacher.phone
        #    }
        return data
    
    def __repr__(self) -> str:
        return f"<Course(course_id={self.course_id}, name={self.course_name}, type={self.course_type.value})>"