from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.work_base import ORMBaseSchema
from app.schemas.work_enums import ProjectStatus


class ProjectCreate(ORMBaseSchema):
    title: str = Field(min_length=1, max_length=255)
    status: ProjectStatus = ProjectStatus.OPEN
    description: str = ""
    managed_by: uuid.UUID


class ProjectRead(ORMBaseSchema):
    project_id: uuid.UUID
    title: str
    status: ProjectStatus
    description: str
    managed_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None
    is_deleted: bool

