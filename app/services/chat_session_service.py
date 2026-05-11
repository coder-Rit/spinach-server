
import uuid
from app.models.chat_session import ChatSession
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class ChatSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, *, page: int, size: int, user_id: uuid.UUID | None = None) -> tuple[int, list[ChatSession]]:
        base = select(ChatSession).where(ChatSession.is_deleted.is_(False))
        if user_id:
            base = base.where(ChatSession.created_by == user_id)
            
        total_stmt = select(func.count()).select_from(base.subquery())
        total = int((await self.db.execute(total_stmt)).scalar_one())

        stmt = (
            base.order_by(ChatSession.created_at.desc(), ChatSession.session_id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

    async def create(self, *, name: str, user_id: uuid.UUID) -> ChatSession:
        session = ChatSession(name=name, created_by=user_id, updated_by=user_id)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get(self, session_id: uuid.UUID) -> ChatSession | None:
        stmt = select(ChatSession).where(ChatSession.session_id == session_id, ChatSession.is_deleted.is_(False))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
