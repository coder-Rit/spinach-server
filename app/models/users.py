from __future__ import annotations

import uuid

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.projects import Project
from app.models.work_items import WorkItem
from app.models.work_mixins import TimestampAuditSoftDeleteMixin


class User(Base, TimestampAuditSoftDeleteMixin):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    managed_projects: Mapped[list["Project"]] = relationship(
        back_populates="manager",
        cascade="all",
        foreign_keys=[Project.managed_by],
    )
    assigned_work_items: Mapped[list["WorkItem"]] = relationship(
        back_populates="assignee",
        cascade="all",
        foreign_keys=[WorkItem.assigned_to],
    )
    created_work_items: Mapped[list["WorkItem"]] = relationship(
        back_populates="assigner",
        cascade="all",
        foreign_keys=[WorkItem.assigned_by],
    )

