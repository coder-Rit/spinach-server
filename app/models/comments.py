from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.work_mixins import TimestampAuditSoftDeleteMixin


class Comment(Base, TimestampAuditSoftDeleteMixin):
    __tablename__ = "comments"

    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("work_items.work_item_id"),
        nullable=False,
        index=True,
    )
    comment_reply_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.comment_id"),
        nullable=True,
        index=True,
    )

    work_item: Mapped["WorkItem"] = relationship(back_populates="comments")
    parent: Mapped[Optional["Comment"]] = relationship(
        remote_side="Comment.comment_id",
        back_populates="replies",
        foreign_keys=[comment_reply_id],
    )
    replies: Mapped[list["Comment"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )

