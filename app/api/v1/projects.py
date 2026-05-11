from app.db.cromadb import upsert_to_collection, delete_from_collection
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.db.session import get_async_session
from app.models.users import User
from app.models.work_enums import ProjectStatus
from app.schemas.projects_api import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectPublic,
    ProjectUpdateRequest,
)
from app.services.project_service import ProjectService


projects_router = APIRouter(prefix="/projects", tags=["Projects"])


@projects_router.post("", response_model=ProjectPublic)
async def create_project(
    payload: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = ProjectService(db)
    project = await service.create(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        managed_by=current_user.user_id,
        created_by=current_user.user_id,
    )

    doc_content = json.dumps(
        {
            "title": project.title,
            "description": project.description,
            "status": project.status.value
            if hasattr(project.status, "value")
            else str(project.status),
            "project_id": str(project.project_id),
            "managed_by": str(project.managed_by),
            "created_by": str(project.created_by),
            "type": "project",
        }
    )

    upsert_to_collection(
        doc_id=str(project.project_id),
        content=doc_content,
        metadata={
            "project_id": str(project.project_id),
            "managed_by": str(project.managed_by),
            "created_by": str(project.created_by),
            "type": "project",
        },
    )

    return ProjectPublic.model_validate(project)


@projects_router.get("", response_model=ProjectListResponse)
async def list_projects(
    search: str | None = Query(default=None, description="Partial match on title"),
    status: ProjectStatus | None = Query(default=None),
    managed_by: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=500),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = ProjectService(db)
    total, projects = await service.list(
        search=search, status=status, managed_by=managed_by, page=page, size=size
    )
    return ProjectListResponse(
        total=total,
        page=page,
        size=size,
        hits=[ProjectPublic.model_validate(p) for p in projects],
    )


@projects_router.get("/{project_id}", response_model=ProjectPublic)
async def get_project(
    project_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectPublic.model_validate(project)


@projects_router.put("/{project_id}", response_model=ProjectPublic)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="Project not found")

    # Basic authz: only manager can update/delete
    if project.managed_by != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    project = await service.update(
        target=project,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        updated_by=current_user.user_id,
    )

    doc_content = json.dumps(
        {
            "title": project.title,
            "description": project.description,
            "status": project.status.value
            if hasattr(project.status, "value")
            else str(project.status),
            "project_id": str(project.project_id),
            "managed_by": str(project.managed_by),
            "created_by": str(project.created_by),
            "type": "project",
        }
    )

    upsert_to_collection(
        doc_id=str(project.project_id),
        content=doc_content,
        metadata={
            "project_id": str(project.project_id),
            "managed_by": str(project.managed_by),
            "created_by": str(project.created_by),
            "type": "project",
        },
    )
    return ProjectPublic.model_validate(project)


@projects_router.delete("/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.managed_by != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    await service.soft_delete(target=project, updated_by=current_user.user_id)
    delete_from_collection(str(project_id))
    return {"message": "Project deleted successfully"}
