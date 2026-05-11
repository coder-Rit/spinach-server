import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from langchain_core.tools import tool

from app.db.session import AsyncSessionLocal
from app.models.work_items import WorkItem
from app.models.work_enums import WorkItemStatus, WorkItemType


@tool
async def find_tasks(
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
    """
    Find work items (tasks, bugs, epics, etc.) by multiple filters.
    
    Args:
        name: Optional partial match on title.
        work_item_ids: Optional list of work item UUID strings.
        project_id: Optional project UUID string.
        display_ids: Optional list of integer display IDs.
        item_types: Optional list of item types ('task', 'bug', 'epic', 'feature').
        statuses: Optional list of statuses ('todo', 'in_progress', 'in_review', 'done').
        start_date: Optional ISO date string boundary (tasks starting on or after this).
        end_date: Optional ISO date string boundary (tasks ending on or before this).
        assigned_by_ids: Optional list of user UUID strings who assigned the task.
        assigned_to_ids: Optional list of user UUID strings assigned to the task.
        linked_work_item_id: Optional linked work item UUID string.
    """
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(WorkItem).where(WorkItem.is_deleted.is_(False))

            if name:
                stmt = stmt.where(WorkItem.title.ilike(f"%{name}%"))
                
            if work_item_ids:
                wids = [uuid.UUID(wid) for wid in work_item_ids]
                stmt = stmt.where(WorkItem.work_item_id.in_(wids))
                
            if project_id:
                stmt = stmt.where(WorkItem.project_id == uuid.UUID(project_id))
                
            if display_ids is not None and len(display_ids) > 0:
                stmt = stmt.where(WorkItem.display_id.in_(display_ids))
                
            if item_types:
                types = [WorkItemType(t.lower()) for t in item_types]
                stmt = stmt.where(WorkItem.item_type.in_(types))
                
            if statuses:
                stats = [WorkItemStatus(s.lower()) for s in statuses]
                stmt = stmt.where(WorkItem.status.in_(stats))
                
            if start_date:
                sd = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                stmt = stmt.where(WorkItem.start_date >= sd)
                
            if end_date:
                ed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                stmt = stmt.where(WorkItem.end_date <= ed)
                
            if assigned_by_ids:
                by_ids = [uuid.UUID(uid) for uid in assigned_by_ids]
                stmt = stmt.where(WorkItem.assigned_by.in_(by_ids))
                
            if assigned_to_ids:
                to_ids = [uuid.UUID(uid) for uid in assigned_to_ids]
                stmt = stmt.where(WorkItem.assigned_to.in_(to_ids))
                
            if linked_work_item_id:
                stmt = stmt.where(WorkItem.linked_work_item_id == uuid.UUID(linked_work_item_id))

            stmt = stmt.distinct()
            result = await db.execute(stmt)
            work_items = result.scalars().all()

            if not work_items:
                return "No work items found matching the given criteria."

            items_dicts = []
            for wi in work_items:
                items_dicts.append({
                    "work_item_id": str(wi.work_item_id),
                    "project_id": str(wi.project_id),
                    "display_id": wi.display_id,
                    "title": wi.title,
                    "item_type": wi.item_type.value if hasattr(wi.item_type, 'value') else str(wi.item_type),
                    "status": wi.status.value if hasattr(wi.status, 'value') else str(wi.status),
                    "assigned_to": str(wi.assigned_to) if wi.assigned_to else None,
                    "assigned_by": str(wi.assigned_by),
                })
                
            return json.dumps(items_dicts, indent=2)

    except ValueError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error finding tasks: {str(e)}"
