from __future__ import annotations

import uuid
from sqlalchemy.orm import aliased

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat, ChatRole


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(
        self,
        *,
        session_id: uuid.UUID,
        page: int,
        size: int,
    ) -> tuple[int, list[Chat]]:
        stmt = select(Chat).where(
            Chat.is_deleted.is_(False), Chat.session_id == session_id
        )

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.db.execute(total_stmt)).scalar_one())

        stmt = (
            stmt.order_by(Chat.created_at.asc(), Chat.chat_id.asc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

 

    async def get_recent(
        self,
        *,
        session_id: uuid.UUID,
        limit: int = 10,
        chat_types: list[ChatRole] | None = None,  # None = fetch all types
    ) -> list[Chat]:

        filters = [
            Chat.is_deleted.is_(False),
            Chat.session_id == session_id,
        ]

        if chat_types:
            filters.append(Chat.role.in_([ct.value for ct in chat_types]))

        recent = (
            select(Chat)
            .where(*filters)
            .order_by(Chat.created_at.desc(), Chat.chat_id.desc())
            .limit(limit)
            .subquery()
        )

        ChatRecent = aliased(Chat, recent)

        stmt = select(ChatRecent).order_by(
            ChatRecent.created_at.asc(),
            ChatRecent.chat_id.asc(),
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        *,
        session_id: uuid.UUID,
        message: str,
        role: ChatRole,
        user_id: uuid.UUID,
        replay_id: uuid.UUID | None = None,
    ) -> Chat:
        chat = Chat(
            session_id=session_id,
            message=message,
            role=role,
            created_by=user_id,
            updated_by=user_id,
            replay_id=replay_id,
        )
        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)
        return chat
