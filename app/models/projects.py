from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, Enum as SAEnum, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.work_enums import ProjectStatus
from app.models.work_mixins import TimestampAuditSoftDeleteMixin


class Project(Base, TimestampAuditSoftDeleteMixin):
    __tablename__ = "projects"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus, name="project_status", native_enum=True),
        nullable=False,
        index=True,
        default=ProjectStatus.OPEN,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    managed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
        index=True,
    )

    manager: Mapped["User"] = relationship(
        back_populates="managed_projects",
        foreign_keys=[managed_by],
    )
    work_items: Mapped[list["WorkItem"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
