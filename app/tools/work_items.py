import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.cromadb import upsert_to_collection
from app.models.projects import Project
from app.models.work_enums import WorkItemStatus, WorkItemType
from app.models.users import User
from app.models.work_items import WorkItem
from app.services.work_item_service import WorkItemService
from app.tools.common import tool_error


async def create_work_item(
    db: AsyncSession,
    current_user: User,
    project_id: str,
    title: str,
    item_type: str = "TASK",
    status: str = "TODO",
    assigned_to_id: Optional[str] = None,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    linked_work_item_id: Optional[str] = None,
) -> str:
    """Create a new work item in the specified project."""
    try:
        parsed_type = WorkItemType(item_type.upper())
        parsed_status = WorkItemStatus(status.upper())
        project_uuid = UUID(project_id)
        linked_uuid = UUID(linked_work_item_id) if linked_work_item_id else None
        assignee_uuid = UUID(assigned_to_id) if assigned_to_id else current_user.user_id

        parsed_start_date = datetime.fromisoformat(start_date) if start_date else None
        parsed_end_date = datetime.fromisoformat(end_date) if end_date else None

        project = (
            await db.execute(
                select(Project).where(
                    Project.project_id == project_uuid,
                    Project.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if not project:
            return f"Project {project_id} not found."

        if linked_uuid:
            linked = (
                await db.execute(
                    select(WorkItem).where(
                        WorkItem.work_item_id == linked_uuid,
                        WorkItem.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if not linked:
                return f"Linked work item {linked_work_item_id} not found."

        assignee = (
            await db.execute(
                select(User).where(
                    User.user_id == assignee_uuid,
                    User.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if not assignee:
            return f"User {assigned_to_id or assignee_uuid} not found."

        service = WorkItemService(db)

        wi = await service.create(
            project_id=project_uuid,
            item_type=parsed_type,
            title=title,
            description=description,
            status=parsed_status,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            assigned_by=current_user.user_id,
            assigned_to=assignee_uuid,
            linked_work_item_id=linked_uuid,
            created_by=current_user.user_id,
        )

        doc_content = json.dumps(
            {
                "title": wi.title,
                "description": wi.description,
                "status": wi.status.value
                if hasattr(wi.status, "value")
                else str(wi.status),
                "item_type": wi.item_type.value
                if hasattr(wi.item_type, "value")
                else str(wi.item_type),
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

        return f"Work item '{wi.title}' created successfully with ID: {wi.work_item_id}"

    except Exception as e:
        return tool_error("creating work item", e)


async def delete_work_item(
    db: AsyncSession,
    current_user: User,
    work_item_id: str,
) -> str:
    """Soft-delete a work item."""
    try:
        wi_uuid = UUID(work_item_id)
        service = WorkItemService(db)
        target = await service.get_by_id(wi_uuid)
        if not target or target.is_deleted:
            return f"Work item {work_item_id} not found."

        await service.soft_delete(target=target, updated_by=current_user.user_id)
        content = json.dumps(
            {
                "title": target.title,
                "description": "DELETED",
                "status": target.status.value,
                "type": "work_item",
            }
        )
        upsert_to_collection(
            doc_id=str(target.work_item_id),
            content=content,
            metadata={"work_item_id": str(target.work_item_id), "deleted": "true"},
        )
        return f"Deleted work item {work_item_id}."
    except Exception as e:
        return tool_error("deleting work item", e)


async def update_work_item(
    db: AsyncSession,
    current_user: User,
    work_item_id: str,
    name: Optional[str] = None,
    item_type: Optional[str] = None,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    assigned_to_id: Optional[str] = None,
) -> str:
    """Update a work item. Only pass fields that should change."""
    try:
        wi_uuid = UUID(work_item_id)
        parsed_type = WorkItemType(item_type.upper()) if item_type else None
        parsed_status = WorkItemStatus(status.upper()) if status else None
        sd = (
            datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            if start_date
            else None
        )
        ed = (
            datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            if end_date
            else None
        )
        assignee_uuid = UUID(assigned_to_id) if assigned_to_id else None

        service = WorkItemService(db)
        target = await service.get_by_id(wi_uuid)
        if not target or target.is_deleted:
            return f"Work item {work_item_id} not found."

        if assignee_uuid:
            assignee = (
                await db.execute(
                    select(User).where(
                        User.user_id == assignee_uuid,
                        User.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if not assignee:
                return f"User {assigned_to_id} not found."

        wi = await service.update(
            target=target,
            item_type=parsed_type,
            title=name,
            description=description,
            status=parsed_status,
            start_date=sd,
            end_date=ed,
            assigned_to=assignee_uuid,
            linked_work_item_id=None,
            updated_by=current_user.user_id,
        )
        content = json.dumps(
            {
                "title": wi.title,
                "description": wi.description,
                "status": wi.status.value
                if hasattr(wi.status, "value")
                else str(wi.status),
                "type": "work_item",
            }
        )
        metadata_updates = {"work_item_id": str(wi.work_item_id)}
        if name:
            metadata_updates["title"] = wi.title
        if status:
            metadata_updates["status"] = (
                wi.status.value if hasattr(wi.status, "value") else str(wi.status)
            )
        if assigned_to_id:
            metadata_updates["assigned_to"] = str(wi.assigned_to)

        upsert_to_collection(
            doc_id=str(wi.work_item_id), content=content, metadata=metadata_updates
        )
        return f"Successfully updated work item {work_item_id}."
    except Exception as e:
        return tool_error("updating work item", e)
