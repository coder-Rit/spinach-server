from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.work_enums import ProjectStatus


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    status: ProjectStatus = ProjectStatus.OPEN


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectPublic(_ORM):
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


class ProjectListResponse(BaseModel):
    total: int
    page: int
    size: int
    hits: list[ProjectPublic]

