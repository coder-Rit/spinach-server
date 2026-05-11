from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.work_enums import ProjectStatus


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        result = await self.db.execute(
            select(Project).where(Project.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        title: str,
        description: str,
        status: ProjectStatus,
        managed_by: uuid.UUID,
        created_by: uuid.UUID | None,
    ) -> Project:
        project = Project(
            title=title,
            description=description,
            status=status,
            managed_by=managed_by,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def list(
        self,
        *,
        search: str | None,
        status: ProjectStatus | None,
        managed_by: uuid.UUID | None,
        page: int,
        size: int,
    ) -> tuple[int, list[Project]]:
        stmt = select(Project).where(Project.is_deleted.is_(False))
        if search:
            stmt = stmt.where(Project.title.ilike(f"%{search}%"))
        if status:
            stmt = stmt.where(Project.status == status)
        if managed_by:
            stmt = stmt.where(Project.managed_by == managed_by)

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.db.execute(total_stmt)).scalar_one())

        stmt = stmt.order_by(Project.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

    async def update(
        self,
        *,
        target: Project,
        title: str | None,
        description: str | None,
        status: ProjectStatus | None,
        updated_by: uuid.UUID | None,
    ) -> Project:
        if title is not None:
            target.title = title
        if description is not None:
            target.description = description
        if status is not None:
            target.status = status
        target.updated_by = updated_by
        self.db.add(target)
        await self.db.commit()
        await self.db.refresh(target)
        return target

    async def soft_delete(self, *, target: Project, updated_by: uuid.UUID | None) -> None:
        if target.is_deleted:
            return
        target.is_deleted = True
        target.updated_by = updated_by
        self.db.add(target)
        await self.db.commit()

