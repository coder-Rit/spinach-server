from __future__ import annotations

import uuid
from datetime import datetime

from app.models.chat import ChatRole
from pydantic import BaseModel, ConfigDict


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ChatSessionCreate(BaseModel):
    name: str


class ChatSessionPublic(_ORM):
    session_id: uuid.UUID
    name: str
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ChatPublic(_ORM):
    chat_id: uuid.UUID
    session_id: uuid.UUID
    message: str
    role: ChatRole
    replay_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponse(BaseModel):
    total: int
    page: int
    size: int
    hits: list[ChatSessionPublic]


class ChatListResponse(BaseModel):
    total: int
    page: int
    size: int
    hits: list[ChatPublic]
