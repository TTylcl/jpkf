"""
dal/models/lesson_consumption_model.py
课时消耗记录表 —— 记录每次消课事件

【设计目的】
✅ 每次消课留痕，方便按教师/学生/课程维度统计
✅ 关联排课和学生选课，可追溯每节课的消耗来源
✅ 支持取消回滚（误操作时标记 cancelled 而非物理删除）

【字段说明】
- schedule_id: 对应排课ID，可追溯是哪节排课触发的消课
- teacher_id: 执行消课的教师ID，用于统计教师课消
- student_id: 被扣课时的学生ID
- consumed_at: 实际消课时间（非排课时间，是教师确认的时间）
- lesson_index: 第几课时，相对于该学生的选课记录（如第3/20课时）
- status: confirmed=已确认扣减 / cancelled=已取消（撤销）
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, Index, String, Integer, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from datetime import datetime
from dal.models.base_model import Base
from dal.models.enums import ConsumptionStatus

if TYPE_CHECKING:
    from dal.models.course_model import Course
    from dal.models.user_model import User

class LessonConsumption(Base):
    __tablename__ = "lesson_consumption"

    __table_args__ = (
        Index("idx_consumption_schedule", "schedule_id"),                   # 按排课查消课记录
        Index("idx_consumption_teacher_date", "teacher_id", "consumed_at"), # 教师消课统计（按时间范围）
        Index("idx_consumption_student", "student_id"),                     # 学生消课记录
        Index("idx_consumption_course", "course_id"),                       # 课程消课统计
        {"comment": "课时消耗记录表 —— 每次消课一条记录，保留教师信息方便统计"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="记录ID")
    schedule_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="对应排课ID（追溯消课来源）")
    course_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("course_info.course_id"), nullable=False, comment="课程ID"
    )
    teacher_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user_info.user_id"), nullable=False, comment="执行消课的教师ID"
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user_info.user_id"), nullable=False, comment="被扣课时的学生ID"
    )
    consumed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, comment="消课确认时间（教师操作的时间）"
    )
    lesson_index: Mapped[Optional[int]] = mapped_column(
        Integer, comment="第几课时（相对于该学生的选课记录，如第3/20课时）"
    )
    status: Mapped[str] = mapped_column(
        String(20), default=ConsumptionStatus.CONFIRMED.value,
        comment="消课状态：confirmed=已确认 / cancelled=已取消"
    )

    # Base 继承的时间字段覆盖（使用 TIMESTAMP 而非 DateTime(timezone=True)）
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, index=True, nullable=True, comment="删除时间"
    )

    # ── 关联查询 ──
    course: Mapped[Optional["Course"]] = relationship(
        foreign_keys=[course_id], lazy="selectin",
    )
    teacher: Mapped[Optional["User"]] = relationship(
        foreign_keys=[teacher_id], lazy="selectin",
    )
    student: Mapped[Optional["User"]] = relationship(
        foreign_keys=[student_id], lazy="selectin",
    )

    def __repr__(self) -> str:
        course_name = self.course.course_name if self.course else f"课程{self.course_id}"
        teacher_name = self.teacher.real_name if self.teacher else f"教师{self.teacher_id}"
        student_name = self.student.real_name if self.student else f"学生{self.student_id}"
        return f"<LessonConsumption(id={self.id}, {course_name}, 教师={teacher_name}, 学生={student_name}, {self.consumed_at})>"