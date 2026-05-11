# from fastapi import Depends, HTTPException, status
# from fastapi.security import HTTPAuthorizationCredentials
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.core.enums import APIUserTypeEnum
# from app.db.session import get_db
# from app.helpers.constants import (
#     MESSAGE_ACCESS_DENIED,
#     MESSAGE_INVALID_API_HEADER,
# )
# from app.core.security import hash_api_key, api_key_header
# from app.helpers.custom_exceptions import CommonHTTPException
# from app.models.api_keys import ApiKeysModel
# from app.services.api_key_service import ApiKeyService


# async def authenticate_api_key(
#     api_key: HTTPAuthorizationCredentials = Depends(api_key_header),
#     db: AsyncSession = Depends(get_db),
# ) -> ApiKeysModel:
#     if not api_key:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=MESSAGE_INVALID_API_HEADER,
#         )

#     key_hash = hash_api_key(api_key)

#     _service = ApiKeyService(db)
#     api_key = await _service.get_one_or_none({"key_hash": key_hash})
#     # Add Worker/Portal Specific Logic when required
#     # if api_key.type == APIUserTypeEnum.WORKER:
#     #     pass

#     if not api_key or not api_key.is_active:
#         response = {"message": MESSAGE_ACCESS_DENIED}
#         raise CommonHTTPException(status.HTTP_401_UNAUTHORIZED, response)

#     return api_key
