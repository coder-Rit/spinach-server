import json
from typing import Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.users import User
from app.models.work_items import WorkItem


async def get_my_info(
    db: AsyncSession,
    current_user: User,
) -> str:
    """Return the current user's profile, managed projects, and workload."""
    try:
        user = (
            await db.execute(
                select(User).where(
                    User.user_id == current_user.user_id,
                    User.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()

        if not user:
            return "User not found."

        projects = (
            (
                await db.execute(
                    select(Project).where(
                        Project.managed_by == current_user.user_id,
                        Project.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )

        work_items = (
            (
                await db.execute(
                    select(WorkItem)
                    .where(
                        WorkItem.assigned_to == current_user.user_id,
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
    except Exception as e:
        return f"Error fetching user info: {str(e)}"


async def find_users(
    db: AsyncSession,
    current_user: User,
    user_ids: Optional[list[str]] = None,
    emails: Optional[list[str]] = None,
    project_id: Optional[str] = None,
    name: Optional[str] = None,
) -> str:
    """Find users by ID, email, name (partial), or project involvement. All filters are optional."""
    try:
        stmt = select(User).where(User.is_deleted.is_(False))

        base_conditions = []
        if user_ids:
            uids = [UUID(uid) for uid in user_ids]
            base_conditions.append(User.user_id.in_(uids))
        if emails:
            base_conditions.append(User.email.in_(emails))
        if name:
            base_conditions.append(User.name.ilike(f"%{name}%"))

        if base_conditions:
            stmt = stmt.where(or_(*base_conditions))

        if project_id:
            pid = UUID(project_id)
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

        user_dicts = [
            {
                "user_id": str(u.user_id),
                "name": u.name,
                "email": u.email,
            }
            for u in users
        ]

        return json.dumps(user_dicts, indent=2)
    except ValueError as e:
        return f"Validation error (invalid UUID format?): {str(e)}"
    except Exception as e:
        return f"Error finding users: {str(e)}"
