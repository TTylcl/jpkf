"""
dal/models/teacher_todo_model.py
教师每日待办表 —— 上课时间到达时自动生成待办项

【设计目的】
✅ 到达上课时间后，后台调度器自动为教师生成"待消课"待办
✅ 教师打开系统即可看到今天需要消几节课、分别是谁
✅ 消课完成后自动标记为 done，待办和消课记录双向关联

【业务流程】
调度器每分钟扫描 → 找到当前时间的排课 → 为每门课的在读学生生成待办
→ 教师消课时 consume_lesson → 待办自动标记完成

【字段说明】
- schedule_id: 关联排课，可追溯到具体哪节课
- student_id: 要消课的学生（一门课可能有多个学生，每人一条待办）
- todo_date: 仅存日期，方便按天查询
- completed_at: 完成时间，用于统计教师每日消课效率
"""
from typing import Optional, TYPE_CHECKING
from datetime import date, datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, Date, Index, ForeignKey, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from dal.models.base_model import Base
from dal.models.enums import TodoStatus

if TYPE_CHECKING:
    from dal.models.user_model import User

class TeacherTodo(Base):
    __tablename__ = "teacher_todo"

    __table_args__ = (
        Index("idx_todo_teacher_date", "teacher_id", "todo_date"),  # 查某教师某天的所有待办
        Index("idx_todo_status", "status"),                          # 按状态筛选
        Index("idx_todo_schedule", "schedule_id"),                   # 按排课查待办
        {"comment": "教师每日待办表 —— 上课时间到达时自动生成，消课完成后自动完成"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="待办ID")
    teacher_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="教师ID")
    schedule_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="关联排课ID")
    course_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="课程ID")
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_info.user_id"), nullable=False, comment="要消课的学生ID")
    todo_date: Mapped[date] = mapped_column(Date, nullable=False, comment="待办日期（格式 YYYY-MM-DD）")
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="待办标题，如：消课：钢琴课 - 小明"
    )
    detail: Mapped[Optional[str]] = mapped_column(
        String(500), comment="待办详情，如课程时间/教室/剩余课时"
    )
    status: Mapped[str] = mapped_column(
        String(20), default=TodoStatus.PENDING.value,
        comment="状态：pending=待处理 / done=已完成 / cancelled=已取消"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True, comment="完成时间（教师确认消课的时间）"
    )

    # Base 继承的时间字段覆盖
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
    student: Mapped[Optional["User"]] = relationship(
        foreign_keys=[student_id],
        lazy="selectin",
    )

    @property
    def student_name(self) -> str:
        if self.student:
            return self.student.real_name
        return f"学生{self.student_id}"

    def __repr__(self) -> str:
        return f"<TeacherTodo(id={self.id}, teacher={self.teacher_id}, date={self.todo_date}, status={self.status}, title={self.title})>"