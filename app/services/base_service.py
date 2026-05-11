import copy
from typing import Generic, Iterable, Optional, Type, TypeVar, Union
from fastapi.responses import JSONResponse
from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import logging as logger

from app.helpers.common import create_json_error_response, get_utc_now
from app.helpers.constants import (
    MESSAGE_PARTIAL_RECORDS_INSERTED,
    MESSAGE_RECORD_ALREADY_EXISTS,
    MESSAGE_RECORD_NOT_INSERTED,
    SQL_ERROR_MESSAGE,
)
from app.helpers.custom_exceptions import CommonHTTPException

logger.getLogger(__name__)

T = TypeVar("T")


class BaseService(Generic[T]):
    def __init__(self, db: AsyncSession, model: Type[T]):
        self.db = db
        self.model = model

    async def create(self, obj: T, return_obj=True) -> tuple:
        try:
            has_error = False
            if isinstance(obj, dict):
                obj_data = obj
            else:
                obj_data = obj.model_dump(exclude_none=True)

            db_obj = self.model(**obj_data)
            self.db.add(db_obj)

            await self.db.commit()
            if return_obj:
                await self.db.refresh(db_obj)
                return db_obj, has_error
        except IntegrityError as e:
            if SQL_ERROR_MESSAGE in e._sql_message():
                has_error = MESSAGE_RECORD_ALREADY_EXISTS
            else:
                logger.error(f"Failed to insert in DB", exc_info=True)
                has_error = MESSAGE_RECORD_NOT_INSERTED
            await self.db.rollback()
        except Exception as e:
            logger.critical(f"Error occured while inserting record: {obj}. ERROR: {e}")
            has_error = MESSAGE_RECORD_NOT_INSERTED
            await self.db.rollback()

        return None, has_error

    async def bulk_create(self, objs: Iterable[T]) -> Union[JSONResponse, list]:
        records_not_inserted = []
        records_inserted = []
        error_message = {}
        for obj in objs:
            if isinstance(obj, dict):
                obj_data = obj
            else:
                obj_data = obj.model_dump(exclude_none=True)
            db_record, has_error = await self.create(obj_data)
            if has_error:
                records_not_inserted.append(
                    dict(error_message=has_error, record=obj_data)
                )
            else:
                records_inserted.append(copy.deepcopy(db_record))

        if records_not_inserted:
            error_details = records_not_inserted

            error_message = create_json_error_response(
                MESSAGE_PARTIAL_RECORDS_INSERTED, 200, error_details
            )

        return records_inserted, error_message

    async def get_one_or_none(self, query: dict, order_by=None) -> Optional[T]:
        if isinstance(query, dict):
            select_query = select(self.model).filter_by(**query)
        else:
            select_query = query

        if order_by is not None:
            select_query = select_query.order_by(order_by)

        record = await self.db.execute(select_query)
        if isinstance(query, dict):
            record = record.scalar_one_or_none()
        else:
            record = record.first()

        return record

    async def get_or_404(self, query: Union[dict, Select]) -> Optional[T]:
        record = await self.get_one_or_none(query)

        if not record:
            error_response = {"message": "No record found."}
            raise CommonHTTPException(404, error_response)

        return record

    async def get_paginated_results(
        self,
        query: Union[Select, dict] = {},
        page: int = 1,
        size: int = 100,
        order_by=None,
    ) -> dict:
        skip = (page - 1) * size
        if isinstance(query, dict):
            select_query = select(self.model).filter_by(**query)
        else:
            select_query = query

        total_count_query = select(func.count()).select_from(select_query)

        if order_by is not None:
            select_query = select_query.order_by(order_by)
        select_query = select_query.offset(skip).limit(size)
        result_obj = await self.db.execute(select_query)
        total_count = await self.db.scalar(total_count_query)

        if isinstance(query, dict):
            hits = result_obj.scalars().all()
        else:
            hits = result_obj.mappings().fetchall()  # .fetchall()

        final_response = {
            "size": size,
            "total": total_count,
            "page": page,
            "hits": hits,
        }

        return final_response

    async def get(
        self,
        query: dict = {},
        skip: int = 0,
        limit: int = 100,
        order_by=None,
    ) -> T:
        if isinstance(query, dict):
            select_query = select(self.model).filter_by(**query)
        else:
            select_query = query

        if order_by is not None:
            select_query = select_query.order_by(order_by)

        select_query = select_query.offset(skip).limit(limit)

        result = await self.db.execute(select_query)

        return result.scalars().all()

    async def get_all(self, query: dict = {}, fetch_many=False, fetch_mappings=False):
        if isinstance(query, dict):
            select_query = select(self.model).filter_by(**query)
        else:
            select_query = query

        result = await self.db.execute(select_query)

        if fetch_many:
            return result.fetchmany()
        elif fetch_mappings:
            return result.mappings().fetchall()
        else:
            return result.scalars().all()

    async def update(
        self,
        record_obj: T,
        obj: Union[T, dict],
    ):
        if isinstance(obj, dict):
            update_data = obj
        else:
            update_data = obj.model_dump(exclude_none=True)

        # Add the updated_at field with the current timestamp
        update_data["updated_at"] = get_utc_now()
        for field in update_data:
            setattr(record_obj, field, update_data[field])
        self.db.add(record_obj)
        await self.db.commit()

    async def delete(self, query: dict) -> bool:
        delete_query = delete(self.model).filter_by(**query)
        record = await self.db.execute(delete_query)
        await self.db.commit()

        return True
