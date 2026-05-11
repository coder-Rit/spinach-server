import uuid

from sqlalchemy import select
from langchain_core.tools import tool

from app.db.session import AsyncSessionLocal
from app.models.work_enums import WorkItemStatus
from app.services.work_item_service import WorkItemService


@tool
async def reassign_work_item(
    user_id: str,
    work_item_id: str,
    assigned_to: str,
) -> str:
    """
    Reassign a work item to a different user.

    Args:
        user_id: UUID of the user performing the reassignment.
        work_item_id: UUID of the work item.
        assigned_to: UUID of the new assignee.
    """
    try:
        user_uuid = uuid.UUID(user_id)
        wi_uuid = uuid.UUID(work_item_id)
        assignee_uuid = uuid.UUID(assigned_to)

        async with AsyncSessionLocal() as db:
            service = WorkItemService(db)
            target = await service.get_by_id(wi_uuid)
            if not target or target.is_deleted:
                return f"Work item {work_item_id} not found."

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
                updated_by=user_uuid,
            )
            return f"Work item '{updated.title}' reassigned to user {assigned_to}."
    except Exception as e:
        return f"Error reassigning work item: {str(e)}"


@tool
async def link_work_items(
    user_id: str,
    work_item_id: str,
    linked_work_item_id: str,
) -> str:
    """
    Link a work item to another work item (parent/dependency relationship).

    Args:
        user_id: UUID of the user performing the link.
        work_item_id: UUID of the child/dependent work item.
        linked_work_item_id: UUID of the parent/linked work item.
    """
    try:
        user_uuid = uuid.UUID(user_id)
        wi_uuid = uuid.UUID(work_item_id)
        linked_uuid = uuid.UUID(linked_work_item_id)

        async with AsyncSessionLocal() as db:
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
                updated_by=user_uuid,
            )
            return f"Work item '{updated.title}' linked to '{linked.title}'."
    except Exception as e:
        return f"Error linking work items: {str(e)}"


@tool
async def bulk_update_status(
    user_id: str,
    work_item_ids: list[str],
    status: str,
) -> str:
    """
    Update the status of multiple work items at once.

    Args:
        user_id: UUID of the user performing the update.
        work_item_ids: List of work item UUID strings to update.
        status: The new status ('TODO', 'IN_PROGRESS', 'CODE_COMPLETE', 'DEPLOYED_ON_STAGE', 'DONE').
    """
    try:
        user_uuid = uuid.UUID(user_id)
        parsed_status = WorkItemStatus(status.upper())
        wi_uuids = [uuid.UUID(wid) for wid in work_item_ids]

        async with AsyncSessionLocal() as db:
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
                    updated_by=user_uuid,
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

            return " | ".join(result_parts)
    except ValueError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error bulk updating status: {str(e)}"


@tool
async def move_work_item(
    user_id: str,
    work_item_id: str,
    new_project_id: str,
) -> str:
    """
    Move a work item to a different project.

    Args:
        user_id: UUID of the user performing the move.
        work_item_id: UUID of the work item to move.
        new_project_id: UUID of the destination project.
    """
    try:
        user_uuid = uuid.UUID(user_id)
        wi_uuid = uuid.UUID(work_item_id)
        new_proj_uuid = uuid.UUID(new_project_id)

        async with AsyncSessionLocal() as db:
            service = WorkItemService(db)
            target = await service.get_by_id(wi_uuid)
            if not target or target.is_deleted:
                return f"Work item {work_item_id} not found."

            # Verify destination project exists
            from app.models.projects import Project

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

            # Get new display_id for destination project
            new_display_id = await service._next_display_id(new_proj_uuid)
            target.project_id = new_proj_uuid
            target.display_id = new_display_id
            target.updated_by = user_uuid
            db.add(target)
            await db.commit()
            await db.refresh(target)

            return f"Work item '{target.title}' moved to project '{proj.title}' with display ID #{new_display_id}."
    except Exception as e:
        return f"Error moving work item: {str(e)}"
