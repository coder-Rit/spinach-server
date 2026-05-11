from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserPublic(_ORM):
    user_id: uuid.UUID
    name: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None
    is_deleted: bool


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None


class UserSearchResponse(BaseModel):
    total: int
    page: int
    size: int
    hits: list[UserPublic]

