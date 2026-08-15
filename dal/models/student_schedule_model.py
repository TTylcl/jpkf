"""
dal/models/student_schedule_model.py
学生排课关联表 —— 将学生绑定到具体的排课时段

【设计目的】
一个课程有多个排课时段，但不是所有学生上所有时段。
这张表把每个学生分配到固定的 1-2 个时段/周，实现：
✅ 学生查课表：只显示自己的时段，不是课程的全部时段
✅ 教师查学生：某个时段有哪些学生来上课
✅ 消课时：知道这个时段该消哪个学生的课时
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from datetime import datetime
from dal.models.base_model import Base

if TYPE_CHECKING:
    from dal.models.user_model import User
    from dal.models.schedule_model import Schedule
    from dal.models.course_model import Course

class StudentSchedule(Base):
    __tablename__ = "student_schedule"

    __table_args__ = (
        Index("idx_ss_student", "student_id"),
        Index("idx_ss_schedule", "schedule_id"),
        UniqueConstraint("student_id", "schedule_id", name="uk_student_schedule"),
        {"comment": "学生排课关联表 —— 每个学生在固定时段上课"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="记录ID")
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user_info.user_id", ondelete="CASCADE"), comment="学生ID"
    )
    schedule_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("schedule.id", ondelete="CASCADE"), comment="排课ID"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, index=True, nullable=True, comment="删除时间"
    )

    # 关联
    student: Mapped[Optional["User"]] = relationship(foreign_keys=[student_id], lazy="selectin")
    schedule: Mapped[Optional["Schedule"]] = relationship(foreign_keys=[schedule_id], lazy="selectin")

    def __repr__(self):
        return f"<StudentSchedule id={self.id} student={self.student_id} schedule={self.schedule_id}>"
