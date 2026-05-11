import json
import uuid
from typing import Optional

from sqlalchemy import select
from langchain_core.tools import tool

from app.db.session import AsyncSessionLocal
from app.models.projects import Project
from app.models.work_enums import ProjectStatus
from app.services.project_service import ProjectService


@tool
async def create_project(
    title: str,
    managed_by: str,
    created_by: str,
    description: str = "",
    status: str = "OPEN",
) -> str:
    """
    Create a new project.

    Args:
        title: The project title.
        managed_by: UUID of the user who manages the project.
        created_by: UUID of the user creating the project.
        description: Optional project description.
        status: Project status ('OPEN' or 'CLOSE'). Defaults to 'OPEN'.
    """
    try:
        managed_uuid = uuid.UUID(managed_by)
        creator_uuid = uuid.UUID(created_by)
        parsed_status = ProjectStatus(status.upper())

        async with AsyncSessionLocal() as db:
            service = ProjectService(db)
            project = await service.create(
                title=title,
                description=description,
                status=parsed_status,
                managed_by=managed_uuid,
                created_by=creator_uuid,
            )
            return f"Project '{project.title}' created successfully with ID: {project.project_id}"
    except ValueError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error creating project: {str(e)}"


@tool
async def update_project(
    user_id: str,
    project_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    """
    Update a project's details. You can update any combination of fields.

    Args:
        user_id: UUID of the user performing the update.
        project_id: UUID of the project to update.
        title: New project title.
        description: New project description.
        status: New status ('OPEN' or 'CLOSE').
    """
    try:
        user_uuid = uuid.UUID(user_id)
        proj_uuid = uuid.UUID(project_id)
        parsed_status = ProjectStatus(status.upper()) if status else None

        async with AsyncSessionLocal() as db:
            service = ProjectService(db)
            target = await service.get_by_id(proj_uuid)
            if not target or target.is_deleted:
                return f"Project {project_id} not found."

            updated = await service.update(
                target=target,
                title=title,
                description=description,
                status=parsed_status,
                updated_by=user_uuid,
            )
            return f"Project '{updated.title}' updated successfully."
    except ValueError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error updating project: {str(e)}"


@tool
async def delete_project(user_id: str, project_id: str) -> str:
    """
    Delete (soft-delete) a project.

    Args:
        user_id: UUID of the user deleting the project.
        project_id: UUID of the project to delete.
    """
    try:
        user_uuid = uuid.UUID(user_id)
        proj_uuid = uuid.UUID(project_id)

        async with AsyncSessionLocal() as db:
            service = ProjectService(db)
            target = await service.get_by_id(proj_uuid)
            if not target or target.is_deleted:
                return f"Project {project_id} not found."

            await service.soft_delete(target=target, updated_by=user_uuid)
            return f"Project '{target.title}' deleted successfully."
    except Exception as e:
        return f"Error deleting project: {str(e)}"


@tool
async def find_projects(
    project_ids: Optional[list[str]] = None,
    project_name: Optional[str] = None,
    managed_by: Optional[str] = None,
    statuses: Optional[list[str]] = None,
) -> str:
    """
    Find projects by IDs, name (partial match), manager, or statuses.

    Args:
        project_ids: Optional list of project UUID strings.
        project_name: Optional string to perform a partial match on the project title.
        managed_by: Optional user UUID string representing the project manager.
        statuses: Optional list of statuses (e.g., 'open', 'closed').
    """
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Project).where(Project.is_deleted.is_(False))

            if project_ids:
                pids = [uuid.UUID(pid) for pid in project_ids]
                stmt = stmt.where(Project.project_id.in_(pids))

            if project_name:
                stmt = stmt.where(Project.title.ilike(f"%{project_name}%"))

            if managed_by:
                managed_uuid = uuid.UUID(managed_by)
                stmt = stmt.where(Project.managed_by == managed_uuid)

            if statuses:
                parsed_statuses = [ProjectStatus(s.lower()) for s in statuses]
                stmt = stmt.where(Project.status.in_(parsed_statuses))

            stmt = stmt.distinct()
            result = await db.execute(stmt)
            projects = result.scalars().all()

            if not projects:
                return "No projects found matching the given criteria."

            project_dicts = []
            for p in projects:
                project_dicts.append(
                    {
                        "project_id": str(p.project_id),
                        "title": p.title,
                        "description": p.description,
                        "status": p.status.value
                        if hasattr(p.status, "value")
                        else str(p.status),
                        "managed_by": str(p.managed_by),
                    }
                )

            return json.dumps(project_dicts, indent=2)

    except ValueError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error finding projects: {str(e)}"
