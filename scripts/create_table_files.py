from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "app"

TEMPLATES = {
    "model": """from sqlalchemy import UUID, Column, String, text
from app.models.base import CustomBaseModel


class [[MODEL]]Model(CustomBaseModel):
    __tablename__ = "[[TABLE]]"
    id = Column(
        UUID, primary_key=True, index=True, server_default=text("gen_random_uuid()")
    )

""",
    "schema": """from pydantic import BaseModel
from typing import Sequence
from app.schemas.base_schema import BasePaginationSchema


class [[MODEL]]PostRequestSchema(BaseModel):
    ...


class [[MODEL]]PutRequestSchema(BaseModel):
    ...


class [[MODEL]]ResponseSchema(BaseModel):
    ...


class [[MODEL]]PaginatedResponseSchema(BasePaginationSchema):
    hits: Sequence[[[MODEL]]ResponseSchema]
""",
    "service": """from sqlalchemy.ext.asyncio import AsyncSession
from app.models.[[MODULE]] import [[MODEL]]Model
from app.services.base_service import BaseService


class [[MODEL]]Service(BaseService[[[MODEL]]Model]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, [[MODEL]]Model)
""",
    "router": """from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.helpers.constants import (
    MESSAGE_RECORD_DELETED,
    MESSAGE_RECORD_INSERTED,
    MESSAGE_RECORD_UPDATED,
)
from fastapi.encoders import jsonable_encoder
from app.schemas.base_schema import BaseResponseSchema, GetRequestPaginationSchema
from app.schemas.[[MODULE]] import (
    [[MODEL]]PostRequestSchema,
    [[MODEL]]PutRequestSchema,
    [[MODEL]]ResponseSchema,
    [[MODEL]]PaginatedResponseSchema,
)
from pydantic import UUID4
from app.services.[[MODULE]]_service import [[MODEL]]Service

router = APIRouter(prefix="/[[MODULE]]s")


@router.post(
    "", response_model=BaseResponseSchema, status_code=status.HTTP_201_CREATED
)
async def create_[[MODULE]]s(
    payload: List[[[MODEL]]PostRequestSchema],
    db: AsyncSession = Depends(get_db),
):
    _service = [[MODEL]]Service(db)
    _, has_error = await _service.bulk_create(payload)
    if has_error:
        return has_error

    return {"message": MESSAGE_RECORD_INSERTED}


@router.get("/{id}", response_model=[[MODEL]]ResponseSchema)
async def get_[[MODULE]](
    id: UUID4,
    db: AsyncSession = Depends(get_db),
):
    _service = [[MODEL]]Service(db)

    record = await _service.get_or_404({"id": id})

    return record


@router.get("", response_model=[[MODEL]]PaginatedResponseSchema)
async def get_[[MODULE]]s(
    pagination: GetRequestPaginationSchema = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # query_params = jsonable_encoder(query_params, exclude_none=True)
    _service = [[MODEL]]Service(db)
    paginated_records = await _service.get_paginated_results(
        page=pagination.page,
        size=pagination.size,
        order_by=desc("created_ts"),
    )
    return paginated_records


@router.put("/{id}", response_model=BaseResponseSchema)
async def update_[[MODULE]](
    id: UUID4,
    payload: [[MODEL]]PutRequestSchema,
    db: AsyncSession = Depends(get_db),
):
    _service = [[MODEL]]Service(db)

    record = await _service.get_or_404({"id": id})

    data_to_update = jsonable_encoder(payload, exclude_none=True)
    if data_to_update:
        await _service.update(record, data_to_update)
    return {"message": MESSAGE_RECORD_UPDATED}


@router.delete("/{id}", response_model=BaseResponseSchema)
async def delete_[[MODULE]](
    id: UUID4,
    db: AsyncSession = Depends(get_db),
):
    _service = [[MODEL]]Service(db)

    _ = await _service.get_or_404({"id": id})

    await _service.delete({"id": id})
    return {"message": MESSAGE_RECORD_DELETED}
""",
}


def snake_case(name: str) -> str:
    return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")


def pluralize(name: str) -> str:
    if name.endswith("y"):
        return name[:-1] + "ies"
    return name + "s"


def create_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.write_text(content)
    print(f"Created {path}")


def main():
    model_name = input("Enter Table / Model name (e.g. User): ").strip()
    if not model_name.isidentifier():
        raise ValueError("Invalid model name")

    module = snake_case(model_name)
    table = pluralize(module)
    plural = pluralize(module)

    create_file(
        BASE_DIR / "models" / f"{module}.py",
        TEMPLATES["model"].replace("[[MODEL]]", model_name).replace("[[TABLE]]", table),
    )

    create_file(
        BASE_DIR / "schemas" / f"{module}.py",
        TEMPLATES["schema"].replace("[[MODEL]]", model_name),
    )

    create_file(
        BASE_DIR / "services" / f"{module}_service.py",
        TEMPLATES["service"]
        .replace("[[MODEL]]", model_name)
        .replace("[[MODULE]]", module),
    )

    create_file(
        BASE_DIR / "api" / "v1" / f"{plural}.py",
        TEMPLATES["router"]
        .replace("[[MODEL]]", model_name)
        .replace("[[MODULE]]", module)
        .replace("[[PLURAL]]", plural),
    )

    print("\n✅ Table scaffold generated successfully")
    print(f"👉 Remember to include the router in app/main.py and model in app/db/base.py")


if __name__ == "__main__":
    main()
