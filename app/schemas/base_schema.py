from typing import Optional
from fastapi import Query
from pydantic import BaseModel


class BaseResponseSchema(BaseModel):
    error: Optional[list] = None
    message: str


class GetRequestPaginationSchema(BaseModel):
    page: int = Query(1, ge=1)
    size: int = Query(10, ge=1, le=500)


class BasePaginationSchema(BaseModel):
    total: Optional[int] = 0
    size: Optional[int] = 10
    page: Optional[int] = 1
