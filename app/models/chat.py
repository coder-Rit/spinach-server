from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import Enum as SAEnum, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.work_mixins import TimestampAuditSoftDeleteMixin


class ChatRole(str, Enum):
    USER = "USER"
    AI = "AI"


class Chat(Base, TimestampAuditSoftDeleteMixin):
    __tablename__ = "chats"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.session_id"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[ChatRole] = mapped_column(
        SAEnum(ChatRole, name="chat_role"),
        nullable=False,
        index=True,
    )
    replay_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chats.chat_id"),
        nullable=True,
        index=True,
    )

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="chats")
    replay: Mapped["Chat | None"] = relationship(
        "Chat",
        remote_side=[chat_id],
        foreign_keys=[replay_id],
    )
