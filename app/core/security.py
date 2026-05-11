from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    *, subject: uuid.UUID, expires_minutes: int | None = None
) -> str:
    expire_minutes = expires_minutes or settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS
    expire_at = datetime.now(tz=timezone.utc) + timedelta(days=expire_minutes)
    payload = {
        "sub": str(subject),
        "exp": expire_at,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])


import hashlib

from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(name="Authorization", scheme_name="API Key Header")


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()
