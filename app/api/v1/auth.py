from app.db.cromadb import upsert_to_collection
import json

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_async_session
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.schemas.user_management import UserPublic
from app.services.auth_service import AuthService


auth_router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer(auto_error=False)


@auth_router.post("/register", response_model=RegisterResponse)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_async_session),
):
    service = AuthService(db)
    user = await service.register(
        name=payload.name, email=str(payload.email), password=payload.password
    )

    doc_content = json.dumps(
        {
            "name": user.name,
            "email": user.email,
            "user_id": str(user.user_id),
            "type": "user",
            "managed_by": str(user.user_id),
        }
    )

    upsert_to_collection(
        doc_id=str(user.user_id),
        content=doc_content,
        metadata={
            "user_id": str(user.user_id),
            "type": "user",
            "managed_by": str(user.user_id),
        },
    )

    return RegisterResponse(user_id=user.user_id, name=user.name, email=user.email)


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_async_session),
):
    service = AuthService(db)
    token = await service.login(email=str(payload.email), password=payload.password)
    return TokenResponse(access_token=token)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_async_session),
):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id = uuid.UUID(str(sub))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    service = AuthService(db)
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@auth_router.get("/me", response_model=UserPublic)
async def get_me(current_user=Depends(get_current_user)):
    return UserPublic.model_validate(current_user)
