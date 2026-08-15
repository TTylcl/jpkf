from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, SmallInteger, String, Text, BigInteger, Index
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from dal.models.base_model import Base
from dal.models.enums import SenderType, MessageType

if TYPE_CHECKING:
    from dal.models.session_info_model import SessionInfo

class ChatMessage(Base):
    __tablename__ = "chat_message"
    
  # ✅ 排除Base的id、以及你表不存在的deleted_at/updated_at
    __mapper_args__ = {"exclude_properties": ["id", "deleted_at", "updated_at"]}
    __table_args__ = (
        Index("idx_chat_message_session_id", "session_id"),
        Index("idx_chat_message_created_at", "created_at"),
        {"comment": "消息记录表"}
    )

    # 主键
    msg_id: Mapped[int] = mapped_column(primary_key=True, comment="消息唯一标识")
    # 外键关联会话
    session_id: Mapped[int] = mapped_column(
        ForeignKey("session_info.session_id", ondelete="CASCADE"),
        comment="会话ID"
    )
    # 业务字段
    sender_type: Mapped[SenderType] = mapped_column(
        PGEnum(SenderType, name="sender_type_enum", create_type=False),
        comment="发送者类型"
    )
    sender_id: Mapped[int | None] = mapped_column(BigInteger, comment="发送者ID")
    message_type: Mapped[MessageType] = mapped_column(
        PGEnum(MessageType, name="message_type_enum", create_type=False),
        default=MessageType.TEXT,
        comment="消息类型"
    )
    content: Mapped[str] = mapped_column(Text, comment="消息内容")
    reference_kb_id: Mapped[int | None] = mapped_column(BigInteger, comment="引用的知识库ID")
    intent: Mapped[str | None] = mapped_column(String(100), comment="识别到的意图")
    is_auto_reply: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        comment="是否AI自动回复"
    )

    # 关联关系
    session: Mapped["SessionInfo"] = relationship(
        "SessionInfo", back_populates="messages"
    )

    # 便捷属性
    @property
    def is_user_message(self) -> bool:
        return self.sender_type == SenderType.USER
    @property
    def is_robot_message(self) -> bool:
        return self.sender_type == SenderType.ROBOT

    def __repr__(self) -> str:
        return f"<ChatMessage(msg_id={self.msg_id}, session_id={self.session_id}, sender={self.sender_type})>"