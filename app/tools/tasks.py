import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.models.work_items import WorkItem
from app.models.work_enums import WorkItemStatus, WorkItemType


async def find_tasks(
    db: AsyncSession,
    current_user: User,
    name: Optional[str] = None,
    work_item_ids: Optional[list[str]] = None,
    project_id: Optional[str] = None,
    display_ids: Optional[list[int]] = None,
    item_types: Optional[list[str]] = None,
    statuses: Optional[list[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    assigned_by_ids: Optional[list[str]] = None,
    assigned_to_ids: Optional[list[str]] = None,
    linked_work_item_id: Optional[str] = None,
) -> str:
    """Find work items by flexible filters. All filters are optional."""
    try:
        stmt = select(WorkItem).where(WorkItem.is_deleted.is_(False))

        if name:
            stmt = stmt.where(WorkItem.title.ilike(f"%{name}%"))

        if work_item_ids:
            wids = [UUID(wid) for wid in work_item_ids]
            stmt = stmt.where(WorkItem.work_item_id.in_(wids))

        if project_id:
            stmt = stmt.where(WorkItem.project_id == UUID(project_id))

        if display_ids:
            stmt = stmt.where(WorkItem.display_id.in_(display_ids))

        if item_types:
            types = [WorkItemType(t.upper()) for t in item_types]
            stmt = stmt.where(WorkItem.item_type.in_(types))

        if statuses:
            stats = [WorkItemStatus(s.upper()) for s in statuses]
            stmt = stmt.where(WorkItem.status.in_(stats))

        if start_date:
            sd = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            stmt = stmt.where(WorkItem.start_date >= sd)

        if end_date:
            ed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            stmt = stmt.where(WorkItem.end_date <= ed)

        if assigned_by_ids:
            by_ids = [UUID(uid) for uid in assigned_by_ids]
            stmt = stmt.where(WorkItem.assigned_by.in_(by_ids))

        if assigned_to_ids:
            to_ids = [UUID(uid) for uid in assigned_to_ids]
            stmt = stmt.where(WorkItem.assigned_to.in_(to_ids))

        if linked_work_item_id:
            stmt = stmt.where(
                WorkItem.linked_work_item_id == UUID(linked_work_item_id)
            )

        stmt = stmt.distinct()
        result = await db.execute(stmt)
        work_items = result.scalars().all()

        if not work_items:
            return "No work items found matching the given criteria."

        items_dicts = [
            {
                "work_item_id": str(wi.work_item_id),
                "project_id": str(wi.project_id),
                "display_id": wi.display_id,
                "title": wi.title,
                "item_type": wi.item_type.value
                if hasattr(wi.item_type, "value")
                else str(wi.item_type),
                "status": wi.status.value
                if hasattr(wi.status, "value")
                else str(wi.status),
                "assigned_to": str(wi.assigned_to) if wi.assigned_to else None,
                "assigned_by": str(wi.assigned_by),
            }
            for wi in work_items
        ]

        return json.dumps(items_dicts, indent=2)
    except ValueError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error finding tasks: {str(e)}"
