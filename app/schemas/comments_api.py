from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CommentCreateRequest(BaseModel):
    comment: str = Field(min_length=1)
    comment_reply_id: Optional[uuid.UUID] = None


class CommentUpdateRequest(BaseModel):
    comment: str = Field(min_length=1)


class CommentPublic(_ORM):
    comment_id: uuid.UUID
    comment: str
    work_item_id: uuid.UUID
    comment_reply_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None
    is_deleted: bool


class CommentListResponse(BaseModel):
    total: int
    page: int
    size: int
    hits: list[CommentPublic]

