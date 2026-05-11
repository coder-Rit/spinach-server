from sqlalchemy import Column, DateTime, func
from app.db.base_class import Base
from sqlalchemy.ext.asyncio import AsyncAttrs

from app.helpers.common import get_utc_now


class CustomBaseModel(Base, AsyncAttrs):
    __abstract__ = True

    created_ts = Column(
        DateTime(timezone=True), default=get_utc_now, server_default=func.now()
    )
    updated_ts = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=func.now(),
        server_default=func.now(),
    )
