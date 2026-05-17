import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.users import User
from app.models.work_items import WorkItem
from app.models.work_enums import WorkItemStatus


async def get_project_summary(
    db: AsyncSession,
    current_user: User,
    project_id: str,
) -> str:
    """Return work item counts by status, type, assignee, and overdue count for a project."""
    try:
        proj_uuid = UUID(project_id)

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

        summary = {
            "project_id": str(project.project_id),
            "title": project.title,
            "status": project.status.value,
            "description": project.description,
            "total_work_items": sum(status_counts.values()),
            "by_status": status_counts,
            "by_type": type_counts,
            "by_assignee": assignee_counts,
            "overdue_count": overdue_count,
        }
        return json.dumps(summary, indent=2)
    except Exception as e:
        return f"Error getting project summary: {str(e)}"


async def get_user_workload(
    db: AsyncSession,
    current_user: User,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    """Return a user's active work items and status breakdown. Defaults to the current user."""
    try:
        user_uuid = UUID(user_id) if user_id else current_user.user_id
        proj_uuid = UUID(project_id) if project_id else None

        user = (
            await db.execute(select(User).where(User.user_id == user_uuid))
        ).scalar_one_or_none()

        if not user:
            return f"User {user_uuid} not found."

        stmt = select(WorkItem.status, func.count()).where(
            WorkItem.assigned_to == user_uuid,
            WorkItem.is_deleted.is_(False),
        )
        if proj_uuid:
            stmt = stmt.where(WorkItem.project_id == proj_uuid)
        stmt = stmt.group_by(WorkItem.status)
        status_rows = (await db.execute(stmt)).all()
        status_counts = {row[0].value: row[1] for row in status_rows}

        items_stmt = select(WorkItem).where(
            WorkItem.assigned_to == user_uuid,
            WorkItem.is_deleted.is_(False),
            WorkItem.status != WorkItemStatus.DONE,
        )
        if proj_uuid:
            items_stmt = items_stmt.where(WorkItem.project_id == proj_uuid)
        items_stmt = items_stmt.order_by(WorkItem.end_date.asc().nullslast())
        items = (await db.execute(items_stmt)).scalars().all()

        item_list = [
            {
                "work_item_id": str(wi.work_item_id),
                "title": wi.title,
                "status": wi.status.value,
                "item_type": wi.item_type.value,
                "end_date": wi.end_date.isoformat() if wi.end_date else None,
                "project_id": str(wi.project_id),
            }
            for wi in items
        ]

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


async def get_overdue_items(
    db: AsyncSession,
    current_user: User,
    project_id: Optional[str] = None,
    assigned_to_id: Optional[str] = None,
) -> str:
    """Return work items past their end date that are not DONE. All filters are optional."""
    try:
        now = datetime.now(timezone.utc)

        stmt = select(WorkItem).where(
            WorkItem.is_deleted.is_(False),
            WorkItem.end_date < now,
            WorkItem.status != WorkItemStatus.DONE,
        )

        if project_id:
            stmt = stmt.where(WorkItem.project_id == UUID(project_id))
        if assigned_to_id:
            stmt = stmt.where(WorkItem.assigned_to == UUID(assigned_to_id))

        stmt = stmt.order_by(WorkItem.end_date.asc())
        items = (await db.execute(stmt)).scalars().all()

        if not items:
            return "No overdue items found."

        item_list = [
            {
                "work_item_id": str(wi.work_item_id),
                "title": wi.title,
                "status": wi.status.value,
                "item_type": wi.item_type.value,
                "end_date": wi.end_date.isoformat() if wi.end_date else None,
                "days_overdue": (now - wi.end_date).days if wi.end_date else 0,
                "assigned_to": str(wi.assigned_to),
                "project_id": str(wi.project_id),
            }
            for wi in items
        ]

        return json.dumps(
            {"total_overdue": len(item_list), "items": item_list}, indent=2
        )
    except Exception as e:
        return f"Error getting overdue items: {str(e)}"
