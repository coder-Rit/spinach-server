from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.work_base import ORMBaseSchema
from app.schemas.work_enums import WorkItemStatus, WorkItemType


class WorkItemCreate(ORMBaseSchema):
    project_id: uuid.UUID
    display_id: int = Field(ge=1)
    item_type: WorkItemType
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    status: WorkItemStatus = WorkItemStatus.TODO
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    assigned_by: uuid.UUID
    assigned_to: uuid.UUID
    linked_work_item_id: Optional[uuid.UUID] = None


class WorkItemRead(ORMBaseSchema):
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

