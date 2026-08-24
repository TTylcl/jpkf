from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, DateTime, BigInteger, Index, SmallInteger
from sqlalchemy.dialects.postgresql import ENUM as PGEnum, TIME
from dal.models.base_model import Base
from dal.models.enums import PreScheduleStatus

if TYPE_CHECKING:
    from dal.models.user_model import User
    from dal.models.course_model import Course

class PreSchedule(Base):
    __tablename__ = "pre_schedule"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True,
        comment="预排课ID"
    )

    __table_args__ = (
        Index("idx_pre_schedule_student_id", "student_id"),
        Index("idx_pre_schedule_course_id", "course_id"),
        Index("idx_pre_schedule_status", "status"),
        {"comment": "预排课表"}
    )

    # 业务字段
    student_id: Mapped[int] = mapped_column(
        ForeignKey("user_info.user_id", ondelete="CASCADE"),
        comment="学生ID"
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("course_info.course_id", ondelete="CASCADE"),
        comment="课程ID"
    )
    preferred_time: Mapped[str | None] = mapped_column(String(100), comment="期望上课时间")
    # 结构化时间字段（由 preferred_time 解析而来，用于冲突检查；老数据可能为 NULL）
    day_of_week: Mapped[int | None] = mapped_column(SmallInteger, comment="期望星期几 1-7")
    start_time: Mapped[object | None] = mapped_column(TIME, comment="期望开始时间")
    end_time: Mapped[object | None] = mapped_column(TIME, comment="期望结束时间")
    preferred_teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_info.user_id", ondelete="SET NULL"),
        comment="期望教师ID"
    )
    status: Mapped[PreScheduleStatus] = mapped_column(
        PGEnum(
            PreScheduleStatus,
            name="schedule_status_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=PreScheduleStatus.PENDING,
        comment="审核状态"
    )
    submit_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="提交时间"
    )
    reviewer_id: Mapped[int | None] = mapped_column(BigInteger, comment="审核人ID")
    review_time: Mapped[datetime | None] = mapped_column(DateTime, comment="审核时间")
    review_note: Mapped[str | None] = mapped_column(String(500), comment="审核备注")

    # 关联关系（单向，不需要 back_populates）
    student: Mapped["User"] = relationship(foreign_keys=[student_id], lazy="selectin")
    preferred_teacher: Mapped["User | None"] = relationship(foreign_keys=[preferred_teacher_id], lazy="selectin")
    course: Mapped["Course"] = relationship(foreign_keys=[course_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<PreSchedule(id={self.id}, student_id={self.student_id}, course_id={self.course_id}, status={self.status})>"