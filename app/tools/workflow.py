from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.users import User
from app.models.work_enums import WorkItemStatus
from app.services.work_item_service import WorkItemService
from app.tools.common import tool_error


async def reassign_work_item(
    db: AsyncSession,
    current_user: User,
    work_item_id: str,
    assigned_to_id: str,
) -> str:
    """Reassign a work item to a different user."""
    try:
        wi_uuid = UUID(work_item_id)
        assignee_uuid = UUID(assigned_to_id)

        service = WorkItemService(db)
        target = await service.get_by_id(wi_uuid)
        if not target or target.is_deleted:
            return f"Work item {work_item_id} not found."

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

        updated = await service.update(
            target=target,
            item_type=None,
            title=None,
            description=None,
            status=None,
            start_date=None,
            end_date=None,
            assigned_to=assignee_uuid,
            linked_work_item_id=None,
            updated_by=current_user.user_id,
        )
        return f"Work item '{updated.title}' reassigned to user {assigned_to_id}."
    except Exception as e:
        return tool_error("reassigning work item", e)


async def link_work_items(
    db: AsyncSession,
    current_user: User,
    work_item_id: str,
    linked_work_item_id: str,
) -> str:
    """Link a work item to another (parent/dependency relationship)."""
    try:
        wi_uuid = UUID(work_item_id)
        linked_uuid = UUID(linked_work_item_id)

        service = WorkItemService(db)
        target = await service.get_by_id(wi_uuid)
        if not target or target.is_deleted:
            return f"Work item {work_item_id} not found."

        linked = await service.get_by_id(linked_uuid)
        if not linked or linked.is_deleted:
            return f"Linked work item {linked_work_item_id} not found."

        updated = await service.update(
            target=target,
            item_type=None,
            title=None,
            description=None,
            status=None,
            start_date=None,
            end_date=None,
            assigned_to=None,
            linked_work_item_id=linked_uuid,
            updated_by=current_user.user_id,
        )
        return f"Work item '{updated.title}' linked to '{linked.title}'."
    except Exception as e:
        return tool_error("linking work items", e)


async def bulk_update_status(
    db: AsyncSession,
    current_user: User,
    work_item_ids: list[str],
    status: str,
) -> str:
    """Update the status of multiple work items at once."""
    try:
        parsed_status = WorkItemStatus(status.upper())
        wi_uuids = [UUID(wid) for wid in work_item_ids]

        service = WorkItemService(db)
        updated_titles = []
        failed = []

        for wi_uuid in wi_uuids:
            target = await service.get_by_id(wi_uuid)
            if not target or target.is_deleted:
                failed.append(str(wi_uuid))
                continue

            await service.update(
                target=target,
                item_type=None,
                title=None,
                description=None,
                status=parsed_status,
                start_date=None,
                end_date=None,
                assigned_to=None,
                linked_work_item_id=None,
                updated_by=current_user.user_id,
            )
            updated_titles.append(target.title)

        result_parts = []
        if updated_titles:
            result_parts.append(
                f"Updated {len(updated_titles)} item(s) to '{parsed_status.value}': {', '.join(updated_titles)}"
            )
        if failed:
            result_parts.append(
                f"Failed to find {len(failed)} item(s): {', '.join(failed)}"
            )

        return " | ".join(result_parts) if result_parts else "No items updated."
    except Exception as e:
        return tool_error("bulk updating status", e)


async def move_work_item(
    db: AsyncSession,
    current_user: User,
    work_item_id: str,
    new_project_id: str,
) -> str:
    """Move a work item to a different project."""
    try:
        wi_uuid = UUID(work_item_id)
        new_proj_uuid = UUID(new_project_id)

        service = WorkItemService(db)
        target = await service.get_by_id(wi_uuid)
        if not target or target.is_deleted:
            return f"Work item {work_item_id} not found."

        proj = (
            await db.execute(
                select(Project).where(
                    Project.project_id == new_proj_uuid,
                    Project.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if not proj:
            return f"Destination project {new_project_id} not found."

        new_display_id = await service._next_display_id(new_proj_uuid)
        target.project_id = new_proj_uuid
        target.display_id = new_display_id
        target.updated_by = current_user.user_id
        db.add(target)
        await db.commit()
        await db.refresh(target)

        return f"Work item '{target.title}' moved to project '{proj.title}' with display ID #{new_display_id}."
    except Exception as e:
        return tool_error("moving work item", e)
