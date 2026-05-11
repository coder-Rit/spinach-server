import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from langchain_core.tools import tool

from app.db.session import AsyncSessionLocal
from app.models.projects import Project
from app.models.users import User
from app.models.work_items import WorkItem
from app.models.work_enums import WorkItemStatus


@tool
async def get_project_summary(project_id: str) -> str:
    """
    Get a summary of a project including work item counts by status, type, and assignee breakdown.

    Args:
        project_id: UUID of the project.
    """
    try:
        proj_uuid = uuid.UUID(project_id)

        async with AsyncSessionLocal() as db:
            # Get project info
            project = (
                await db.execute(
                    select(Project).where(
                        Project.project_id == proj_uuid,
                        Project.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()

            if not project:
                return f"Project {project_id} not found."

            # Count by status
            status_stmt = (
                select(WorkItem.status, func.count())
                .where(
                    WorkItem.project_id == proj_uuid,
                    WorkItem.is_deleted.is_(False),
                )
                .group_by(WorkItem.status)
            )
            status_rows = (await db.execute(status_stmt)).all()
            status_counts = {row[0].value: row[1] for row in status_rows}

            # Count by type
            type_stmt = (
                select(WorkItem.item_type, func.count())
                .where(
                    WorkItem.project_id == proj_uuid,
                    WorkItem.is_deleted.is_(False),
                )
                .group_by(WorkItem.item_type)
            )
            type_rows = (await db.execute(type_stmt)).all()
            type_counts = {row[0].value: row[1] for row in type_rows}

            # Count by assignee
            assignee_stmt = (
                select(User.name, func.count())
                .join(WorkItem, WorkItem.assigned_to == User.user_id)
                .where(
                    WorkItem.project_id == proj_uuid,
                    WorkItem.is_deleted.is_(False),
                )
                .group_by(User.name)
            )
            assignee_rows = (await db.execute(assignee_stmt)).all()
            assignee_counts = {row[0]: row[1] for row in assignee_rows}

            # Overdue count
            now = datetime.now(timezone.utc)
            overdue_stmt = (
                select(func.count())
                .select_from(WorkItem)
                .where(
                    WorkItem.project_id == proj_uuid,
                    WorkItem.is_deleted.is_(False),
                    WorkItem.end_date < now,
                    WorkItem.status != WorkItemStatus.DONE,
                )
            )
            overdue_count = (await db.execute(overdue_stmt)).scalar_one()

            total_items = sum(status_counts.values())

            summary = {
                "project_id": str(project.project_id),
                "title": project.title,
                "status": project.status.value,
                "description": project.description,
                "total_work_items": total_items,
                "by_status": status_counts,
                "by_type": type_counts,
                "by_assignee": assignee_counts,
                "overdue_count": overdue_count,
            }
            return json.dumps(summary, indent=2)
    except Exception as e:
        return f"Error getting project summary: {str(e)}"


@tool
async def get_user_workload(
    user_id: str,
    project_id: Optional[str] = None,
) -> str:
    """
    Get a user's workload — their assigned work items with status breakdown.

    Args:
        user_id: UUID of the user.
        project_id: Optional UUID to scope workload to a specific project.
    """
    try:
        user_uuid = uuid.UUID(user_id)
        proj_uuid = uuid.UUID(project_id) if project_id else None

        async with AsyncSessionLocal() as db:
            # Get user name
            user = (
                await db.execute(select(User).where(User.user_id == user_uuid))
            ).scalar_one_or_none()

            if not user:
                return f"User {user_id} not found."

            # Status breakdown
            stmt = select(WorkItem.status, func.count()).where(
                WorkItem.assigned_to == user_uuid,
                WorkItem.is_deleted.is_(False),
            )
            if proj_uuid:
                stmt = stmt.where(WorkItem.project_id == proj_uuid)
            stmt = stmt.group_by(WorkItem.status)
            status_rows = (await db.execute(stmt)).all()
            status_counts = {row[0].value: row[1] for row in status_rows}

            # Get active items (not DONE)
            items_stmt = select(WorkItem).where(
                WorkItem.assigned_to == user_uuid,
                WorkItem.is_deleted.is_(False),
                WorkItem.status != WorkItemStatus.DONE,
            )
            if proj_uuid:
                items_stmt = items_stmt.where(WorkItem.project_id == proj_uuid)
            items_stmt = items_stmt.order_by(WorkItem.end_date.asc().nullslast())
            items = (await db.execute(items_stmt)).scalars().all()

            item_list = []
            for wi in items:
                item_list.append(
                    {
                        "work_item_id": str(wi.work_item_id),
                        "title": wi.title,
                        "status": wi.status.value,
                        "item_type": wi.item_type.value,
                        "end_date": wi.end_date.isoformat() if wi.end_date else None,
                        "project_id": str(wi.project_id),
                    }
                )

            result = {
                "user_id": str(user.user_id),
                "user_name": user.name,
                "total_active": len(items),
                "by_status": status_counts,
                "active_items": item_list,
            }
            return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting user workload: {str(e)}"


@tool
async def get_overdue_items(
    project_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
) -> str:
    """
    Get work items that are past their end date but not yet done.

    Args:
        project_id: Optional UUID to scope to a specific project.
        assigned_to: Optional user UUID to scope to a specific assignee.
    """
    try:
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            stmt = select(WorkItem).where(
                WorkItem.is_deleted.is_(False),
                WorkItem.end_date < now,
                WorkItem.status != WorkItemStatus.DONE,
            )

            if project_id:
                stmt = stmt.where(WorkItem.project_id == uuid.UUID(project_id))
            if assigned_to:
                stmt = stmt.where(WorkItem.assigned_to == uuid.UUID(assigned_to))

            stmt = stmt.order_by(WorkItem.end_date.asc())
            items = (await db.execute(stmt)).scalars().all()

            if not items:
                return "No overdue items found."

            item_list = []
            for wi in items:
                days_overdue = (now - wi.end_date).days if wi.end_date else 0
                item_list.append(
                    {
                        "work_item_id": str(wi.work_item_id),
                        "title": wi.title,
                        "status": wi.status.value,
                        "item_type": wi.item_type.value,
                        "end_date": wi.end_date.isoformat() if wi.end_date else None,
                        "days_overdue": days_overdue,
                        "assigned_to": str(wi.assigned_to),
                        "project_id": str(wi.project_id),
                    }
                )

            return json.dumps(
                {"total_overdue": len(item_list), "items": item_list}, indent=2
            )
    except Exception as e:
        return f"Error getting overdue items: {str(e)}"
