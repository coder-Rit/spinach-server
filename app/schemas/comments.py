from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.work_base import ORMBaseSchema


class CommentCreate(ORMBaseSchema):
    comment: str = Field(min_length=1)
    work_item_id: uuid.UUID
    comment_reply_id: Optional[uuid.UUID] = None


class CommentRead(ORMBaseSchema):
    comment_id: uuid.UUID
    comment: str
    work_item_id: uuid.UUID
    comment_reply_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None
    is_deleted: bool

