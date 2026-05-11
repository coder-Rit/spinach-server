from __future__ import annotations

import json
import uuid

from app.db.cromadb import upsert_to_collection, delete_from_collection
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.db.session import get_async_session
from app.models.users import User
from app.models.work_enums import WorkItemStatus, WorkItemType
from app.schemas.work_items_api import (
    WorkItemCreateRequest,
    WorkItemListResponse,
    WorkItemPublic,
    WorkItemUpdateRequest,
)
from app.services.work_item_service import WorkItemService


work_items_router = APIRouter(prefix="/work-items", tags=["WorkItems"])


@work_items_router.post("/projects/{project_id}", response_model=WorkItemPublic)
async def create_work_item(
    project_id: uuid.UUID,
    payload: WorkItemCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = WorkItemService(db)
    wi = await service.create(
        project_id=project_id,
        item_type=payload.item_type,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        assigned_by=current_user.user_id,
        assigned_to=payload.assigned_to,
        linked_work_item_id=payload.linked_work_item_id,
        created_by=current_user.user_id,
    )

    doc_content = json.dumps(
        {
            "title": wi.title,
            "description": wi.description,
            "status": wi.status.value if hasattr(wi.status, "value") else str(wi.status),
            "item_type": wi.item_type.value if hasattr(wi.item_type, "value") else str(wi.item_type),
            "work_item_id": str(wi.work_item_id),
            "project_id": str(wi.project_id),
            "assigned_to": str(wi.assigned_to) if wi.assigned_to else "",
            "assigned_by": str(wi.assigned_by),
            "created_by": str(wi.created_by),
            "type": "work_item",
        }
    )

    upsert_to_collection(
        doc_id=str(wi.work_item_id),
        content=doc_content,
        metadata={
            "work_item_id": str(wi.work_item_id),
            "project_id": str(wi.project_id),
            "assigned_to": str(wi.assigned_to) if wi.assigned_to else "",
            "assigned_by": str(wi.assigned_by),
            "created_by": str(wi.created_by),
            "type": "work_item",
        },
    )

    return WorkItemPublic.model_validate(wi)


@work_items_router.get("", response_model=WorkItemListResponse)
async def list_work_items(
    project_id: uuid.UUID | None = Query(default=None),
    status: WorkItemStatus | None = Query(default=None),
    item_type: WorkItemType | None = Query(default=None),
    assigned_to: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, description="Search title/description"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=500),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = WorkItemService(db)
    total, items = await service.list(
        project_id=project_id,
        status=status,
        item_type=item_type,
        assigned_to=assigned_to,
        search=search,
        page=page,
        size=size,
    )
    return WorkItemListResponse(
        total=total,
        page=page,
        size=size,
        hits=[WorkItemPublic.model_validate(w) for w in items],
    )


@work_items_router.get("/{work_item_id}", response_model=WorkItemPublic)
async def get_work_item(
    work_item_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = WorkItemService(db)
    wi = await service.get_by_id(work_item_id)
    if not wi or wi.is_deleted:
        raise HTTPException(status_code=404, detail="Work item not found")
    return WorkItemPublic.model_validate(wi)


@work_items_router.put("/{work_item_id}", response_model=WorkItemPublic)
async def update_work_item(
    work_item_id: uuid.UUID,
    payload: WorkItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = WorkItemService(db)
    wi = await service.get_by_id(work_item_id)
    if not wi or wi.is_deleted:
        raise HTTPException(status_code=404, detail="Work item not found")

    # Basic authz: allow assigner to update
    if wi.assigned_by != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    wi = await service.update(
        target=wi,
        item_type=payload.item_type,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        assigned_to=payload.assigned_to,
        linked_work_item_id=payload.linked_work_item_id,
        updated_by=current_user.user_id,
    )

    doc_content = json.dumps(
        {
            "title": wi.title,
            "description": wi.description,
            "status": wi.status.value if hasattr(wi.status, "value") else str(wi.status),
            "item_type": wi.item_type.value if hasattr(wi.item_type, "value") else str(wi.item_type),
            "work_item_id": str(wi.work_item_id),
            "project_id": str(wi.project_id),
            "assigned_to": str(wi.assigned_to) if wi.assigned_to else "",
            "assigned_by": str(wi.assigned_by),
            "created_by": str(wi.created_by),
            "type": "work_item",
        }
    )

    upsert_to_collection(
        doc_id=str(wi.work_item_id),
        content=doc_content,
        metadata={
            "work_item_id": str(wi.work_item_id),
            "project_id": str(wi.project_id),
            "assigned_to": str(wi.assigned_to) if wi.assigned_to else "",
            "assigned_by": str(wi.assigned_by),
            "created_by": str(wi.created_by),
            "type": "work_item",
        },
    )

    return WorkItemPublic.model_validate(wi)


@work_items_router.delete("/{work_item_id}")
async def delete_work_item(
    work_item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = WorkItemService(db)
    wi = await service.get_by_id(work_item_id)
    if not wi or wi.is_deleted:
        raise HTTPException(status_code=404, detail="Work item not found")

    if wi.assigned_by != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    await service.soft_delete(target=wi, updated_by=current_user.user_id)
    delete_from_collection(str(work_item_id))
    return {"message": "Work item deleted successfully"}

