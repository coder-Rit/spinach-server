from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comments import Comment
from app.models.work_items import WorkItem


class CommentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, comment_id: uuid.UUID) -> Comment | None:
        result = await self.db.execute(
            select(Comment).where(Comment.comment_id == comment_id)
        )
        return result.scalar_one_or_none()

    async def list_for_work_item(
        self,
        *,
        work_item_id: uuid.UUID,
        page: int,
        size: int,
    ) -> tuple[int, list[Comment]]:
        # ensure work item exists (and not deleted)
        wi = await self.db.execute(
            select(WorkItem).where(
                WorkItem.work_item_id == work_item_id, WorkItem.is_deleted.is_(False)
            )
        )
        if not wi.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Work item not found")

        stmt = (
            select(Comment)
            .where(Comment.work_item_id == work_item_id, Comment.is_deleted.is_(False))
            .order_by(Comment.created_at.asc())
        )
        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.db.execute(total_stmt)).scalar_one())

        stmt = stmt.offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

    async def create(
        self,
        *,
        work_item_id: uuid.UUID,
        comment: str,
        comment_reply_id: uuid.UUID | None,
        created_by: uuid.UUID | None,
    ) -> Comment:
        # ensure work item exists (and not deleted)
        wi = await self.db.execute(
            select(WorkItem).where(
                WorkItem.work_item_id == work_item_id, WorkItem.is_deleted.is_(False)
            )
        )
        if not wi.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Work item not found")

        if comment_reply_id is not None:
            parent = await self.get_by_id(comment_reply_id)
            if not parent or parent.is_deleted or parent.work_item_id != work_item_id:
                raise HTTPException(status_code=400, detail="Invalid comment_reply_id")

        c = Comment(
            work_item_id=work_item_id,
            comment=comment,
            comment_reply_id=comment_reply_id,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(c)
        await self.db.commit()
        await self.db.refresh(c)
        return c

    async def update(
        self,
        *,
        target: Comment,
        comment: str,
        updated_by: uuid.UUID | None,
    ) -> Comment:
        target.comment = comment
        target.updated_by = updated_by
        self.db.add(target)
        await self.db.commit()
        await self.db.refresh(target)
        return target

    async def soft_delete(self, *, target: Comment, updated_by: uuid.UUID | None) -> None:
        if target.is_deleted:
            return
        target.is_deleted = True
        target.updated_by = updated_by
        self.db.add(target)
        await self.db.commit()

