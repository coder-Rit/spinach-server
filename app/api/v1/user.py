from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.db.session import get_async_session
from app.models.users import User
from app.schemas.user_management import UserPublic, UserSearchResponse, UserUpdateRequest
from app.services.user_service import UserService


user_router = APIRouter(prefix="/user", tags=["User"])


@user_router.get("", response_model=UserSearchResponse)
async def search_users(
    search: str | None = Query(default=None, description="Search by name or email (partial match)"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=500),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = UserService(db)
    total, users = await service.search(search=search, page=page, size=size)
    return UserSearchResponse(
        total=total,
        page=page,
        size=size,
        hits=[UserPublic.model_validate(u) for u in users],
    )


@user_router.put("/{id}", response_model=UserPublic)
async def update_user(
    id: uuid.UUID,
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    if current_user.user_id != id:
        raise HTTPException(status_code=403, detail="Forbidden")

    service = UserService(db)
    target = await service.get_by_id(id)
    if not target or target.is_deleted:
        raise HTTPException(status_code=404, detail="User not found")

    updated = await service.update_user(
        target=target,
        name=payload.name,
        email=str(payload.email) if payload.email is not None else None,
        updated_by=current_user.user_id,
    )
    return UserPublic.model_validate(updated)


@user_router.delete("/{id}")
async def delete_user(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    if current_user.user_id != id:
        raise HTTPException(status_code=403, detail="Forbidden")

    service = UserService(db)
    target = await service.get_by_id(id)
    if not target or target.is_deleted:
        raise HTTPException(status_code=404, detail="User not found")

    await service.soft_delete(target=target, updated_by=current_user.user_id)
    return {"message": "User deleted successfully"}

