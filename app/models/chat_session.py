import uuid

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.work_mixins import TimestampAuditSoftDeleteMixin


class ChatSession(Base, TimestampAuditSoftDeleteMixin):
    __tablename__ = "chat_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    chats: Mapped[list["Chat"]] = relationship(
        "Chat",
        back_populates="session",
        cascade="all, delete-orphan",
    )
