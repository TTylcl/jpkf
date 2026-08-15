from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, SmallInteger, String, DateTime, Index
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from dal.models.base_model import Base
from dal.models.enums import SessionType

if TYPE_CHECKING:
    from dal.models.user_model import User
    from dal.models.chat_message_model import ChatMessage

class SessionInfo(Base):
    __tablename__ = "session_info"
    
    # ✅ 排除Base的id、以及你表不存在的deleted_at/updated_at
    __mapper_args__ = {"exclude_properties": ["id", "deleted_at", "updated_at"]}
    __table_args__ = (
        Index("idx_session_info_user_id", "user_id"),
        Index("idx_session_info_status", "status"),
        Index("idx_session_info_start_time", "start_time"),
        Index("idx_session_info_thread_id", "thread_id"),
        {"comment": "会话信息表"}
    )

    # 主键
    session_id: Mapped[int] = mapped_column(primary_key=True, comment="会话唯一标识")
    # 外键关联用户
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_info.user_id", ondelete="CASCADE"),
        comment="用户ID"
    )
    # 业务字段
    session_type: Mapped[SessionType] = mapped_column(
        PGEnum(SessionType, name="session_type_enum", create_type=False),
        default=SessionType.AI_SERVICE,
        comment="会话类型"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        comment="会话状态：active-进行中，closed-已关闭"
    )
    start_time: Mapped[datetime] = mapped_column(DateTime, comment="会话开始时间")
    end_time: Mapped[datetime | None] = mapped_column(DateTime, comment="会话结束时间")
    satisfaction_score: Mapped[int | None] = mapped_column(
        SmallInteger,
        comment="满意度评分（1-5）"
    )
    thread_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="LangGraph checkpoint thread_id，关联多轮对话"
    )
    # 关联关系
    user: Mapped["User"] = relationship("User", backref="sessions")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SessionInfo(session_id={self.session_id}, user_id={self.user_id}, type={self.session_type})>"