from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.db.session import get_async_session
from app.models.users import User
from app.schemas.chats import ChatListResponse, ChatPublic, ChatSessionListResponse, ChatSessionPublic
from app.services.chat_service import ChatService
from app.services.chat_session_service import ChatSessionService


chats_router = APIRouter(prefix="/chats", tags=["Chats"])


@chats_router.get("", response_model=ChatListResponse)
async def list_chats(
    session_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=500),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = ChatService(db)
    total, items = await service.list(session_id=session_id, page=page, size=size)
    return ChatListResponse(
        total=total,
        page=page,
        size=size,
        hits=[ChatPublic.model_validate(i) for i in items],
    )


@chats_router.get("/sessions", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = ChatSessionService(db)
    total, items = await service.list(page=page, size=size)
    return ChatSessionListResponse(
        total=total,
        page=page,
        size=size,
        hits=[ChatSessionPublic.model_validate(i) for i in items],
    )

 