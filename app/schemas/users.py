from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field

from app.schemas.work_base import ORMBaseSchema


class UserCreate(ORMBaseSchema):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=6, max_length=255)


class UserRead(ORMBaseSchema):
    user_id: uuid.UUID
    name: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None
    is_deleted: bool

