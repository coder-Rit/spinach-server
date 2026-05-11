from __future__ import annotations

import json
import uuid

from app.db.cromadb import upsert_to_collection, delete_from_collection
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.db.session import get_async_session
from app.models.users import User
from app.schemas.comments_api import (
    CommentCreateRequest,
    CommentListResponse,
    CommentPublic,
    CommentUpdateRequest,
)
from app.services.comment_service import CommentService


comments_router = APIRouter(prefix="/comments", tags=["Comments"])


@comments_router.post("/work-items/{work_item_id}", response_model=CommentPublic)
async def create_comment(
    work_item_id: uuid.UUID,
    payload: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = CommentService(db)
    c = await service.create(
        work_item_id=work_item_id,
        comment=payload.comment,
        comment_reply_id=payload.comment_reply_id,
        created_by=current_user.user_id,
    )

    doc_content = json.dumps(
        {
            "comment": c.comment,
            "work_item_id": str(c.work_item_id),
            "comment_id": str(c.comment_id),
            "created_by": str(c.created_by),
            "type": "comment",
        }
    )

    upsert_to_collection(
        doc_id=str(c.comment_id),
        content=doc_content,
        metadata={
            "work_item_id": str(c.work_item_id),
            "comment_id": str(c.comment_id),
            "created_by": str(c.created_by),
            "type": "comment",
        },
    )

    return CommentPublic.model_validate(c)


@comments_router.get("/work-items/{work_item_id}", response_model=CommentListResponse)
async def list_comments(
    work_item_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=500),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = CommentService(db)
    total, comments = await service.list_for_work_item(work_item_id=work_item_id, page=page, size=size)
    return CommentListResponse(
        total=total,
        page=page,
        size=size,
        hits=[CommentPublic.model_validate(c) for c in comments],
    )


@comments_router.get("/{comment_id}", response_model=CommentPublic)
async def get_comment(
    comment_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = CommentService(db)
    c = await service.get_by_id(comment_id)
    if not c or c.is_deleted:
        raise HTTPException(status_code=404, detail="Comment not found")
    return CommentPublic.model_validate(c)


@comments_router.put("/{comment_id}", response_model=CommentPublic)
async def update_comment(
    comment_id: uuid.UUID,
    payload: CommentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = CommentService(db)
    c = await service.get_by_id(comment_id)
    if not c or c.is_deleted:
        raise HTTPException(status_code=404, detail="Comment not found")

    if c.created_by != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    c = await service.update(target=c, comment=payload.comment, updated_by=current_user.user_id)

    doc_content = json.dumps(
        {
            "comment": c.comment,
            "work_item_id": str(c.work_item_id),
            "comment_id": str(c.comment_id),
            "created_by": str(c.created_by),
            "type": "comment",
        }
    )

    upsert_to_collection(
        doc_id=str(c.comment_id),
        content=doc_content,
        metadata={
            "work_item_id": str(c.work_item_id),
            "comment_id": str(c.comment_id),
            "created_by": str(c.created_by),
            "type": "comment",
        },
    )

    return CommentPublic.model_validate(c)


@comments_router.delete("/{comment_id}")
async def delete_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = CommentService(db)
    c = await service.get_by_id(comment_id)
    if not c or c.is_deleted:
        raise HTTPException(status_code=404, detail="Comment not found")

    if c.created_by != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    await service.soft_delete(target=c, updated_by=current_user.user_id)
    delete_from_collection(str(comment_id))
    return {"message": "Comment deleted successfully"}

