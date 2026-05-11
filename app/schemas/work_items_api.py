from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.work_enums import WorkItemStatus, WorkItemType


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class WorkItemCreateRequest(BaseModel):
    item_type: WorkItemType
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    status: WorkItemStatus = WorkItemStatus.TODO
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    assigned_to: uuid.UUID
    linked_work_item_id: Optional[uuid.UUID] = None


class WorkItemUpdateRequest(BaseModel):
    item_type: Optional[WorkItemType] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[WorkItemStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    assigned_to: Optional[uuid.UUID] = None
    linked_work_item_id: Optional[uuid.UUID] = None


class WorkItemPublic(_ORM):
    work_item_id: uuid.UUID
    project_id: uuid.UUID
    display_id: int
    item_type: WorkItemType
    title: str
    description: str
    status: WorkItemStatus
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    assigned_by: uuid.UUID
    assigned_to: uuid.UUID
    linked_work_item_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None
    is_deleted: bool


class WorkItemListResponse(BaseModel):
    total: int
    page: int
    size: int
    hits: list[WorkItemPublic]

