import json
import uuid
from typing import Optional

from sqlalchemy import or_, select

from langchain_core.tools import tool
from app.db.session import AsyncSessionLocal
from app.models.projects import Project
from app.models.users import User
from app.models.work_items import WorkItem


@tool
async def get_my_info(user_id: str) -> str:
    """
    Get the current user's own profile along with their assigned work items,
    managed projects, and a workload summary.

    Args:
        user_id: UUID of the current user (self).
    """
    try:
        user_uuid = uuid.UUID(user_id)

        async with AsyncSessionLocal() as db:
            user = (
                await db.execute(
                    select(User).where(
                        User.user_id == user_uuid, User.is_deleted.is_(False)
                    )
                )
            ).scalar_one_or_none()

            if not user:
                return f"User {user_id} not found."

            # Managed projects
            projects = (
                (
                    await db.execute(
                        select(Project).where(
                            Project.managed_by == user_uuid,
                            Project.is_deleted.is_(False),
                        )
                    )
                )
                .scalars()
                .all()
            )

            # Assigned active work items
            work_items = (
                (
                    await db.execute(
                        select(WorkItem)
                        .where(
                            WorkItem.assigned_to == user_uuid,
                            WorkItem.is_deleted.is_(False),
                        )
                        .order_by(WorkItem.end_date.asc().nullslast())
                    )
                )
                .scalars()
                .all()
            )

            status_breakdown: dict[str, int] = {}
            items_list = []
            for wi in work_items:
                s = wi.status.value
                status_breakdown[s] = status_breakdown.get(s, 0) + 1
                items_list.append(
                    {
                        "work_item_id": str(wi.work_item_id),
                        "title": wi.title,
                        "item_type": wi.item_type.value,
                        "status": s,
                        "project_id": str(wi.project_id),
                        "end_date": wi.end_date.isoformat() if wi.end_date else None,
                    }
                )

            result = {
                "user_id": str(user.user_id),
                "name": user.name,
                "email": user.email,
                "managed_projects": [
                    {
                        "project_id": str(p.project_id),
                        "title": p.title,
                        "status": p.status.value,
                    }
                    for p in projects
                ],
                "workload": {
                    "total": len(work_items),
                    "by_status": status_breakdown,
                    "work_items": items_list,
                },
            }
            return json.dumps(result, indent=2)

    except ValueError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error fetching user info: {str(e)}"


@tool
async def find_users(
    user_ids: Optional[list[str]] = None,
    emails: Optional[list[str]] = None,
    project_id: Optional[str] = None,
) -> str:
    """
    Find users by their user_id, email, or involvement in a particular project.

    Args:
        user_ids: Optional list of user UUID strings.
        emails: Optional list of email strings.
        project_id: Optional project UUID string to scope users who are involved in the project (manager or assigned to work items).
    """
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(User).where(User.is_deleted.is_(False))

            base_conditions = []
            if user_ids:
                uids = [uuid.UUID(uid) for uid in user_ids]
                base_conditions.append(User.user_id.in_(uids))
            if emails:
                base_conditions.append(User.email.in_(emails))

            if base_conditions:
                # If they provide ids or emails, match any of them
                stmt = stmt.where(or_(*base_conditions))

            if project_id:
                pid = uuid.UUID(project_id)
                # Left join to find associations with the project directly or via work items
                stmt = stmt.outerjoin(Project, Project.managed_by == User.user_id)
                stmt = stmt.outerjoin(
                    WorkItem,
                    or_(
                        WorkItem.assigned_to == User.user_id,
                        WorkItem.assigned_by == User.user_id,
                    ),
                )
                stmt = stmt.where(
                    or_(Project.project_id == pid, WorkItem.project_id == pid)
                )

            stmt = stmt.distinct()
            result = await db.execute(stmt)
            users = result.scalars().all()

            if not users:
                return "No users found matching the given criteria."

            user_dicts = []
            for u in users:
                user_dicts.append(
                    {
                        "user_id": str(u.user_id),
                        "name": u.name,
                        "email": u.email,
                    }
                )

            return json.dumps(user_dicts, indent=2)

    except ValueError as e:
        return f"Validation error (invalid UUID format?): {str(e)}"
    except Exception as e:
        return f"Error finding users: {str(e)}"
