import json
import uuid
from datetime import datetime
from typing import Optional

from app.db.cromadb import upsert_to_collection
from app.db.session import AsyncSessionLocal
from langchain_core.tools import tool
from app.models.work_enums import WorkItemStatus, WorkItemType
from app.services.work_item_service import WorkItemService


@tool
async def create_work_item(
    project_id: str,
    title: str,
    item_type: str,
    assigned_to: str,
    assigned_by: str,
    created_by: str,
    description: str = "",
    status: str = "todo",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    linked_work_item_id: Optional[str] = None,
) -> str:
    """
    Create a new work item (task, bug, epic, etc.) in the specified project.
    
    Args:
        project_id: The UUID of the project.
        title: The title of the work item.
        item_type: The type of the work item (e.g., 'task', 'bug', 'epic', 'feature').
        assigned_to: The UUID of the user the item is assigned to.
        assigned_by: The UUID of the user assigning the item.
        created_by: The UUID of the user creating the item.
        description: A detailed description of the work item.
        status: The initial status of the work item (e.g., 'todo', 'in_progress', 'done').
        start_date: The start date in ISO format (e.g., '2023-01-01T00:00:00').
        end_date: The end date in ISO format.
        linked_work_item_id: The UUID of another work item this is linked to.
    """
    try:
        proj_uuid = uuid.UUID(project_id)
        assignee_uuid = uuid.UUID(assigned_to)
        assigner_uuid = uuid.UUID(assigned_by)
        creator_uuid = uuid.UUID(created_by)
        linked_uuid = uuid.UUID(linked_work_item_id) if linked_work_item_id else None
        
        parsed_start_date = datetime.fromisoformat(start_date) if start_date else None
        parsed_end_date = datetime.fromisoformat(end_date) if end_date else None
        
        parsed_item_type = WorkItemType(item_type)
        parsed_status = WorkItemStatus(status)
        
        async with AsyncSessionLocal() as db:
            service = WorkItemService(db)
            wi = await service.create(
                project_id=proj_uuid,
                item_type=parsed_item_type,
                title=title,
                description=description,
                status=parsed_status,
                start_date=parsed_start_date,
                end_date=parsed_end_date,
                assigned_by=assigner_uuid,
                assigned_to=assignee_uuid,
                linked_work_item_id=linked_uuid,
                created_by=creator_uuid,
            )
            
            # Upsert into vector DB for semantic search
            doc_content = json.dumps({
                "title": wi.title,
                "description": wi.description,
                "status": wi.status.value if hasattr(wi.status, "value") else str(wi.status),
                "item_type": wi.item_type.value if hasattr(wi.item_type, "value") else str(wi.item_type),
                "work_item_id": str(wi.work_item_id),
                "project_id": str(wi.project_id),
                "assigned_to": str(wi.assigned_to) if wi.assigned_to else "",
                "assigned_by": str(wi.assigned_by),
                "created_by": str(wi.created_by),
                "type": "work_item",
            })
            
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
            
    except ValueError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error creating work item: {str(e)}"

@tool
async def delete_work_item(user_id: str, work_item_id: str) -> str:
    """
    Delete a work item.
    Args:
        user_id: The UUID of the user deleting the item.
        work_item_id: The UUID of the work item.
    """
    try:
        user_uuid = uuid.UUID(user_id)
        wi_uuid = uuid.UUID(work_item_id)
        async with AsyncSessionLocal() as db:
            service = WorkItemService(db)
            target = await service.get_by_id(wi_uuid)
            if not target:
                return f"Work item {work_item_id} not found."
            
            await service.soft_delete(target=target, updated_by=user_uuid)
            content = json.dumps({"title": target.title, "description": "DELETED", "status": target.status.value, "type": "work_item"})
            upsert_to_collection(doc_id=str(target.work_item_id), content=content, metadata={"work_item_id": str(target.work_item_id), "deleted": "true"})
            return f"Deleted work item {work_item_id}."
    except Exception as e:
        return f"Error deleting work item: {str(e)}"

@tool
async def update_work_item(
    user_id: str, 
    work_item_id: str,
    name: Optional[str] = None,
    item_type: Optional[str] = None,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None
) -> str:
    """
    Update a work item's details. You can update any combination of fields.
    Args:
        user_id: The UUID of the user updating the item.
        work_item_id: The UUID of the work item.
        name: The new title/name of the item.
        item_type: The new type (task, bug, etc.)
        description: The new description.
        start_date: Optional start date in ISO format.
        end_date: Optional end date in ISO format.
        status: The new status string (todo, in_progress, in_review, done).
        assigned_to: The UUID of the user to assign this item to.
    """
    try:
        user_uuid = uuid.UUID(user_id)
        wi_uuid = uuid.UUID(work_item_id)
        
        parsed_type = WorkItemType(item_type) if item_type else None
        parsed_status = WorkItemStatus(status) if status else None
        sd = datetime.fromisoformat(start_date.replace("Z", "+00:00")) if start_date else None
        ed = datetime.fromisoformat(end_date.replace("Z", "+00:00")) if end_date else None
        assignee_uuid = uuid.UUID(assigned_to) if assigned_to else None
        
        async with AsyncSessionLocal() as db:
            service = WorkItemService(db)
            target = await service.get_by_id(wi_uuid)
            if not target:
                return f"Work item {work_item_id} not found."
            
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
                updated_by=user_uuid
            )
            content = json.dumps({
                "title": wi.title, 
                "description": wi.description, 
                "status": wi.status.value if hasattr(wi.status, 'value') else str(wi.status), 
                "type": "work_item"
            })
            metadata_updates = {"work_item_id": str(wi.work_item_id)}
            if name: metadata_updates["title"] = wi.title
            if status: metadata_updates["status"] = wi.status.value if hasattr(wi.status, 'value') else str(wi.status)
            if assigned_to: metadata_updates["assigned_to"] = str(wi.assigned_to)
            
            upsert_to_collection(doc_id=str(wi.work_item_id), content=content, metadata=metadata_updates)
            return f"Successfully updated work item {work_item_id}."
    except Exception as e:
        return f"Error updating work item: {str(e)}"

