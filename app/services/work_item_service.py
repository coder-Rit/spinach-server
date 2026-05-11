from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.work_enums import WorkItemStatus, WorkItemType
from app.models.work_items import WorkItem


class WorkItemService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, work_item_id: uuid.UUID) -> WorkItem | None:
        result = await self.db.execute(
            select(WorkItem).where(WorkItem.work_item_id == work_item_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        project_id: uuid.UUID | None,
        status: WorkItemStatus | None,
        item_type: WorkItemType | None,
        assigned_to: uuid.UUID | None,
        search: str | None,
        page: int,
        size: int,
    ) -> tuple[int, list[WorkItem]]:
        stmt = select(WorkItem).where(WorkItem.is_deleted.is_(False))
        if project_id:
            stmt = stmt.where(WorkItem.project_id == project_id)
        if status:
            stmt = stmt.where(WorkItem.status == status)
        if item_type:
            stmt = stmt.where(WorkItem.item_type == item_type)
        if assigned_to:
            stmt = stmt.where(WorkItem.assigned_to == assigned_to)
        if search:
            stmt = stmt.where(
                or_(
                    WorkItem.title.ilike(f"%{search}%"),
                    WorkItem.description.ilike(f"%{search}%"),
                )
            )

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.db.execute(total_stmt)).scalar_one())

        stmt = stmt.order_by(WorkItem.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

    async def _next_display_id(self, project_id: uuid.UUID) -> int:
        # Lock the project row to reduce race on per-project display_id.
        project = await self.db.execute(
            select(Project).where(and_(Project.project_id == project_id, Project.is_deleted.is_(False))).with_for_update()
        )
        if not project.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Project not found")

        max_stmt = select(func.max(WorkItem.display_id)).where(WorkItem.project_id == project_id)
        max_val = (await self.db.execute(max_stmt)).scalar_one()
        return int((max_val or 0) + 1)

    async def create(
        self,
        *,
        project_id: uuid.UUID,
        item_type: WorkItemType,
        title: str,
        description: str,
        status: WorkItemStatus,
        start_date,
        end_date,
        assigned_by: uuid.UUID,
        assigned_to: uuid.UUID,
        linked_work_item_id: uuid.UUID | None,
        created_by: uuid.UUID | None,
    ) -> WorkItem:
        display_id = await self._next_display_id(project_id)
        wi = WorkItem(
            project_id=project_id,
            display_id=display_id,
            item_type=item_type,
            title=title,
            description=description,
            status=status,
            start_date=start_date,
            end_date=end_date,
            assigned_by=assigned_by,
            assigned_to=assigned_to,
            linked_work_item_id=linked_work_item_id,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(wi)
        await self.db.commit()
        await self.db.refresh(wi)
        return wi

    async def update(
        self,
        *,
        target: WorkItem,
        item_type: WorkItemType | None,
        title: str | None,
        description: str | None,
        status: WorkItemStatus | None,
        start_date,
        end_date,
        assigned_to: uuid.UUID | None,
        linked_work_item_id: uuid.UUID | None,
        updated_by: uuid.UUID | None,
    ) -> WorkItem:
        if item_type is not None:
            target.item_type = item_type
        if title is not None:
            target.title = title
        if description is not None:
            target.description = description
        if status is not None:
            target.status = status
        if start_date is not None:
            target.start_date = start_date
        if end_date is not None:
            target.end_date = end_date
        if assigned_to is not None:
            target.assigned_to = assigned_to
        if linked_work_item_id is not None:
            target.linked_work_item_id = linked_work_item_id

        target.updated_by = updated_by
        self.db.add(target)
        await self.db.commit()
        await self.db.refresh(target)
        return target

    async def soft_delete(self, *, target: WorkItem, updated_by: uuid.UUID | None) -> None:
        if target.is_deleted:
            return
        target.is_deleted = True
        target.updated_by = updated_by
        self.db.add(target)
        await self.db.commit()

