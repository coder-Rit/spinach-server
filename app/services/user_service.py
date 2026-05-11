from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        search: str | None,
        page: int,
        size: int,
    ) -> tuple[int, list[User]]:
        stmt = select(User).where(User.is_deleted.is_(False))

        if search:
            stmt = stmt.where(
                or_(
                    User.name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                )
            )

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.db.execute(total_stmt)).scalar_one())

        stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

    async def update_user(
        self,
        *,
        target: User,
        name: str | None,
        email: str | None,
        updated_by: uuid.UUID | None,
    ) -> User:
        if email and email != target.email:
            existing = await self.get_by_email(email)
            if existing and existing.user_id != target.user_id:
                raise HTTPException(status_code=400, detail="Email already registered")
            target.email = email

        if name is not None:
            target.name = name

        target.updated_by = updated_by
        self.db.add(target)
        await self.db.commit()
        await self.db.refresh(target)
        return target

    async def soft_delete(self, *, target: User, updated_by: uuid.UUID | None) -> None:
        if target.is_deleted:
            return
        target.is_deleted = True
        target.updated_by = updated_by
        self.db.add(target)
        await self.db.commit()

