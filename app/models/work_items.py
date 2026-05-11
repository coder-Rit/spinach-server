from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.comments import Comment
from app.models.work_enums import WorkItemStatus, WorkItemType
from app.models.work_mixins import TimestampAuditSoftDeleteMixin


class WorkItem(Base, TimestampAuditSoftDeleteMixin):
    __tablename__ = "work_items"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "display_id", name="uq_work_items_project_display"
        ),
        Index("ix_work_items_project_display", "project_id", "display_id"),
    )

    work_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.project_id"),
        nullable=False,
        index=True,
    )
    display_id: Mapped[int] = mapped_column(Integer, nullable=False)

    item_type: Mapped[WorkItemType] = mapped_column(
        SAEnum(WorkItemType, name="work_item_type", native_enum=True),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[WorkItemStatus] = mapped_column(
        SAEnum(WorkItemStatus, name="work_item_status", native_enum=True),
        nullable=False,
        index=True,
        default=WorkItemStatus.TODO,
    )
    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
        index=True,
    )
    linked_work_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("work_items.work_item_id"),
        nullable=True,
        index=True,
    )

    project: Mapped["Project"] = relationship(back_populates="work_items")
    assigner: Mapped["User"] = relationship(
        back_populates="created_work_items", foreign_keys=[assigned_by]
    )
    assignee: Mapped["User"] = relationship(
        back_populates="assigned_work_items", foreign_keys=[assigned_to]
    )

    linked_work_item: Mapped[Optional["WorkItem"]] = relationship(
        remote_side="WorkItem.work_item_id",
        back_populates="linked_children",
        foreign_keys=[linked_work_item_id],
    )
    linked_children: Mapped[list["WorkItem"]] = relationship(
        back_populates="linked_work_item",
        cascade="all",
    )

    comments: Mapped[list["Comment"]] = relationship(
        back_populates="work_item",
        cascade="all, delete-orphan",
    )
