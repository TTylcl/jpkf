#dal/models/schedule_model.py

"""
dal/models/schedule_model.py
正式排课表模型
✅ 100%对齐schedule表结构
"""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, SmallInteger, BigInteger, Index
from sqlalchemy.dialects.postgresql import TIME
from dal.models.base_model import Base
from dal.models.enums import ScheduleActiveStatus


class Schedule(Base):
    __tablename__ = "schedule"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True,
        comment="排课ID"
    )
    course_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
        comment="课程ID"
    )
    teacher_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
        comment="教师ID"
    )
    day_of_week: Mapped[int] = mapped_column(
        SmallInteger, nullable=False,
        comment="星期几：1=周一, 2=周二 ... 7=周日"
    )
    start_time: Mapped[object] = mapped_column(
        TIME, nullable=False,
        comment="上课开始时间"
    )
    end_time: Mapped[object] = mapped_column(
        TIME, nullable=False,
        comment="上课结束时间"
    )
    classroom: Mapped[str | None] = mapped_column(
        String(50),
        comment="教室"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, default=ScheduleActiveStatus.ACTIVE.value,
        comment="状态：1=有效, 0=停用"
    )
    # created_at / updated_at / deleted_at 从 Base 继承

    __table_args__ = (
        Index("idx_schedule_day_of_week", "day_of_week"),
        Index("idx_schedule_course_id", "course_id"),
        {"comment": "正式排课表"},
    )

   
    def __repr__(self) -> str:
        return f"<Schedule id={self.id} course_id={self.course_id} day={self.day_of_week}>"
