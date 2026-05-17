import json
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.users import User
from app.models.work_enums import ProjectStatus
from app.services.project_service import ProjectService


async def create_project(
    db: AsyncSession,
    current_user: User,
    title: str,
    description: str = "",
    status: str = "OPEN",
    managed_by_id: Optional[str] = None,
) -> str:
    """Create a new project. Manager defaults to the current user."""
    try:
        manager_uuid = UUID(managed_by_id) if managed_by_id else current_user.user_id
        parsed_status = ProjectStatus(status.upper())

        service = ProjectService(db)
        project = await service.create(
            title=title,
            description=description,
            status=parsed_status,
            managed_by=manager_uuid,
            created_by=current_user.user_id,
        )
        return f"Project '{project.title}' created successfully with ID: {project.project_id}"
    except ValueError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error creating project: {str(e)}"


async def update_project(
    db: AsyncSession,
    current_user: User,
    project_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    """Update a project. Only pass fields that should change."""
    try:
        proj_uuid = UUID(project_id)
        parsed_status = ProjectStatus(status.upper()) if status else None

        service = ProjectService(db)
        target = await service.get_by_id(proj_uuid)
        if not target or target.is_deleted:
            return f"Project {project_id} not found."

        updated = await service.update(
            target=target,
            title=title,
            description=description,
            status=parsed_status,
            updated_by=current_user.user_id,
        )
        return f"Project '{updated.title}' updated successfully."
    except ValueError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error updating project: {str(e)}"


async def delete_project(
    db: AsyncSession,
    current_user: User,
    project_id: str,
) -> str:
    """Soft-delete a project."""
    try:
        proj_uuid = UUID(project_id)

        service = ProjectService(db)
        target = await service.get_by_id(proj_uuid)
        if not target or target.is_deleted:
            return f"Project {project_id} not found."

        await service.soft_delete(target=target, updated_by=current_user.user_id)
        return f"Project '{target.title}' deleted successfully."
    except Exception as e:
        return f"Error deleting project: {str(e)}"


async def find_projects(
    db: AsyncSession,
    current_user: User,
    project_ids: Optional[list[str]] = None,
    project_name: Optional[str] = None,
    managed_by_id: Optional[str] = None,
    statuses: Optional[list[str]] = None,
) -> str:
    """Find projects by IDs, partial name, manager, or status. All filters are optional."""
    try:
        stmt = select(Project).where(Project.is_deleted.is_(False))

        if project_ids:
            pids = [UUID(pid) for pid in project_ids]
            stmt = stmt.where(Project.project_id.in_(pids))

        if project_name:
            stmt = stmt.where(Project.title.ilike(f"%{project_name}%"))

        if managed_by_id:
            stmt = stmt.where(Project.managed_by == UUID(managed_by_id))

        if statuses:
            parsed_statuses = [ProjectStatus(s.upper()) for s in statuses]
            stmt = stmt.where(Project.status.in_(parsed_statuses))

        stmt = stmt.distinct()
        result = await db.execute(stmt)
        projects = result.scalars().all()

        if not projects:
            return "No projects found matching the given criteria."

        project_dicts = [
            {
                "project_id": str(p.project_id),
                "title": p.title,
                "description": p.description,
                "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                "managed_by": str(p.managed_by),
            }
            for p in projects
        ]

        return json.dumps(project_dicts, indent=2)
    except ValueError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error finding projects: {str(e)}"
