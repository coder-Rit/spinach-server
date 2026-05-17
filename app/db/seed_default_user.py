from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.cromadb import document_exists, upsert_to_collection
from app.helpers.log_helper import get_logger
from app.models.users import User

logger = get_logger()


def _default_user_doc(user: User) -> str:
    return json.dumps(
        {
            "name": user.name,
            "email": user.email,
            "user_id": str(user.user_id),
            "type": "user",
            "managed_by": str(user.user_id),
        }
    )


def _default_user_metadata(user: User) -> dict:
    return {
        "user_id": str(user.user_id),
        "type": "user",
        "managed_by": str(user.user_id),
    }


def ensure_default_user_in_chroma(user: User) -> None:
    """Upsert the default user into ChromaDB (creates if missing, updates if present)."""
    doc_id = str(user.user_id)
    if document_exists(doc_id):
        logger.info("Default user already in ChromaDB (%s), syncing document", doc_id)
    else:
        logger.info("Default user missing in ChromaDB, creating document %s", doc_id)

    upsert_to_collection(
        doc_id=doc_id,
        content=_default_user_doc(user),
        metadata=_default_user_metadata(user),
    )


async def ensure_default_user_in_postgres(session: AsyncSession) -> User:
    """Create the default user in PostgreSQL if missing."""
    result = await session.execute(
        select(User).where(User.email == settings.default_user_email)
    )
    user = result.scalar_one_or_none()

    if user:
        if user.is_deleted:
            user.is_deleted = False
            user.name = settings.default_user_name
            user.password = hash_password(settings.default_user_password)
            user.updated_at = datetime.now(tz=timezone.utc)
            await session.commit()
            await session.refresh(user)
            logger.info("Reactivated default user in PostgreSQL: %s", user.email)
        else:
            logger.info("Default user already in PostgreSQL: %s", user.email)
        return user

    now = datetime.now(tz=timezone.utc)
    user = User(
        name=settings.default_user_name,
        email=settings.default_user_email,
        password=hash_password(settings.default_user_password),
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        result = await session.execute(
            select(User).where(User.email == settings.default_user_email)
        )
        user = result.scalar_one()
        if not user:
            raise
        logger.info("Default user created concurrently, loaded from PostgreSQL")
        return user

    await session.refresh(user)
    logger.info("Created default user in PostgreSQL: %s (%s)", user.name, user.email)
    return user


async def ensure_default_user(session: AsyncSession) -> User:
    """
    Ensure the default demo user exists in PostgreSQL and ChromaDB.
    Idempotent: safe to run on every server startup.
    """
    user = await ensure_default_user_in_postgres(session)
    try:
        ensure_default_user_in_chroma(user)
    except Exception:
        logger.exception(
            "Failed to sync default user %s into ChromaDB", user.user_id
        )
        raise
    return user
