import json
import uuid
from typing import Optional

from langchain_core.tools import tool

from app.db.session import AsyncSessionLocal
from app.services.comment_service import CommentService


@tool
async def add_comment(
    work_item_id: str,
    comment: str,
    created_by: str,
    comment_reply_id: Optional[str] = None,
) -> str:
    """
    Add a comment to a work item.

    Args:
        work_item_id: UUID of the work item to comment on.
        comment: The comment text.
        created_by: UUID of the user adding the comment.
        comment_reply_id: Optional UUID of a parent comment to reply to (for threaded comments).
    """
    try:
        wi_uuid = uuid.UUID(work_item_id)
        creator_uuid = uuid.UUID(created_by)
        reply_uuid = uuid.UUID(comment_reply_id) if comment_reply_id else None

        async with AsyncSessionLocal() as db:
            service = CommentService(db)
            c = await service.create(
                work_item_id=wi_uuid,
                comment=comment,
                comment_reply_id=reply_uuid,
                created_by=creator_uuid,
            )
            return f"Comment added successfully with ID: {c.comment_id}"
    except Exception as e:
        return f"Error adding comment: {str(e)}"


@tool
async def list_comments(
    work_item_id: str,
    page: int = 1,
    size: int = 20,
) -> str:
    """
    List comments on a work item.

    Args:
        work_item_id: UUID of the work item.
        page: Page number (default 1).
        size: Number of comments per page (default 20).
    """
    try:
        wi_uuid = uuid.UUID(work_item_id)

        async with AsyncSessionLocal() as db:
            service = CommentService(db)
            total, comments = await service.list_for_work_item(
                work_item_id=wi_uuid, page=page, size=size
            )

            if not comments:
                return "No comments found for this work item."

            comment_dicts = []
            for c in comments:
                comment_dicts.append(
                    {
                        "comment_id": str(c.comment_id),
                        "comment": c.comment,
                        "created_by": str(c.created_by) if c.created_by else None,
                        "created_at": c.created_at.isoformat()
                        if c.created_at
                        else None,
                        "reply_to": str(c.comment_reply_id)
                        if c.comment_reply_id
                        else None,
                    }
                )

            return json.dumps({"total": total, "comments": comment_dicts}, indent=2)
    except Exception as e:
        return f"Error listing comments: {str(e)}"


@tool
async def delete_comment(user_id: str, comment_id: str) -> str:
    """
    Delete (soft-delete) a comment.

    Args:
        user_id: UUID of the user deleting the comment.
        comment_id: UUID of the comment to delete.
    """
    try:
        user_uuid = uuid.UUID(user_id)
        comment_uuid = uuid.UUID(comment_id)

        async with AsyncSessionLocal() as db:
            service = CommentService(db)
            target = await service.get_by_id(comment_uuid)
            if not target or target.is_deleted:
                return f"Comment {comment_id} not found."

            await service.soft_delete(target=target, updated_by=user_uuid)
            return f"Comment {comment_id} deleted successfully."
    except Exception as e:
        return f"Error deleting comment: {str(e)}"
