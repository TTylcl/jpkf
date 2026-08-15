from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, DateTime, Index, String, Integer,text,func
from datetime import datetime
from sqlalchemy.dialects.postgresql import TIMESTAMP
from dal.models.base_model import Base
from dal.models.enums import StudentCourseStatus

if TYPE_CHECKING:
    from dal.models.course_model import Course
    from dal.models.user_model import User

class StudentCourse(Base):
    __tablename__ = "student_courses"

    __table_args__ = (
       
        Index(
            "uk_student_course", 
            "student_id", "course_id", 
            unique=True,
            postgresql_where=text("deleted_at IS NULL")  # 只有未删除的才校验唯一
        ),
        Index("idx_status", "status"),
        Index("idx_deleted_at", "deleted_at"),
        {"comment": "学生选课表"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_info.user_id", ondelete="CASCADE"), comment="学生ID")
    course_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("course_info.course_id", ondelete="CASCADE"), comment="课程ID")
    enrolled_at: Mapped[Optional[str]] = mapped_column(TIMESTAMP, comment="选课时间")
    status: Mapped[str] = mapped_column(
        String(20), 
        default=StudentCourseStatus.ACTIVE.value, 
        comment="选课状态：active/cancelled/expired"
    )
    purchased_lessons: Mapped[Optional[int]] = mapped_column(Integer, comment="购买课时")
    remaining_lessons: Mapped[Optional[int]] = mapped_column(Integer, comment="剩余课时")
    # ✅ 优化4：补全软删架构必须的三个通用时间字段
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
    def is_active(self) -> bool:
        return self.status == StudentCourseStatus.ACTIVE.value

    # ✅ 关联课程表，方便取 course_name
    course: Mapped[Optional["Course"]] = relationship(
        foreign_keys=[course_id],
        lazy="selectin",
    )

    # ✅ 关联用户表，方便取 student_name
    student: Mapped[Optional["User"]] = relationship(
        foreign_keys=[student_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        student_name = self.student.real_name if self.student else f"学生{self.student_id}"
        course_name = self.course.course_name if self.course else f"课程{self.course_id}"
        return f"<StudentCourse(id={self.id}, student={student_name}, course={course_name}, status={self.status})>"