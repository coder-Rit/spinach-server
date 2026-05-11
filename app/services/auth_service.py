from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.users import User


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def register(self, *, name: str, email: str, password: str) -> User:
        existing = await self.get_user_by_email(email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(name=name, email=email, password=hash_password(password))
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=400, detail="Email already registered")

        await self.db.refresh(user)
        return user

    async def login(self, *, email: str, password: str) -> str:
        user = await self.get_user_by_email(email)
        if not user or not verify_password(password, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return create_access_token(subject=user.user_id)

