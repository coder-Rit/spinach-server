import json
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.models.work_items import WorkItem
from app.services.comment_service import CommentService
from app.tools.common import tool_error


async def _work_item_missing_message(
    db: AsyncSession, work_item_id: str, wi_uuid: UUID
) -> str | None:
    wi = (
        await db.execute(
            select(WorkItem).where(
                WorkItem.work_item_id == wi_uuid,
                WorkItem.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if wi is None:
        return f"Work item {work_item_id} not found."
    return None


async def add_comment(
    db: AsyncSession,
    current_user: User,
    work_item_id: str,
    comment: str,
    comment_reply_id: Optional[str] = None,
) -> str:
    """Add a comment or threaded reply to a work item."""
    try:
        wi_uuid = UUID(work_item_id)
        reply_uuid = UUID(comment_reply_id) if comment_reply_id else None

        missing = await _work_item_missing_message(db, work_item_id, wi_uuid)
        if missing:
            return missing

        service = CommentService(db)
        c = await service.create(
            work_item_id=wi_uuid,
            comment=comment,
            comment_reply_id=reply_uuid,
            created_by=current_user.user_id,
        )
        return f"Comment added successfully with ID: {c.comment_id}"
    except Exception as e:
        return tool_error("adding comment", e)


async def list_comments(
    db: AsyncSession,
    current_user: User,
    work_item_id: str,
    page: int = 1,
    size: int = 20,
) -> str:
    """List comments on a work item."""
    try:
        wi_uuid = UUID(work_item_id)

        missing = await _work_item_missing_message(db, work_item_id, wi_uuid)
        if missing:
            return missing

        service = CommentService(db)
        total, comments = await service.list_for_work_item(
            work_item_id=wi_uuid, page=page, size=size
        )

        if not comments:
            return "No comments found for this work item."

        comment_dicts = [
            {
                "comment_id": str(c.comment_id),
                "comment": c.comment,
                "created_by": str(c.created_by) if c.created_by else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "reply_to": str(c.comment_reply_id) if c.comment_reply_id else None,
            }
            for c in comments
        ]

        return json.dumps({"total": total, "comments": comment_dicts}, indent=2)
    except Exception as e:
        return tool_error("listing comments", e)


async def delete_comment(
    db: AsyncSession,
    current_user: User,
    comment_id: str,
) -> str:
    """Soft-delete a comment."""
    try:
        comment_uuid = UUID(comment_id)

        service = CommentService(db)
        target = await service.get_by_id(comment_uuid)
        if not target or target.is_deleted:
            return f"Comment {comment_id} not found."

        await service.soft_delete(target=target, updated_by=current_user.user_id)
        return f"Comment {comment_id} deleted successfully."
    except Exception as e:
        return tool_error("deleting comment", e)
