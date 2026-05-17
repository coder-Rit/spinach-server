from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic_core import ValidationError
from app.api.v1.api_v1 import api_v1_router

# from app.core.auth import authenticate_api_key
from app.core.config import settings
from app.db.seed_default_user import ensure_default_user
from app.db.session import AsyncSessionLocal, pg_engine
from app.helpers.common import create_json_error_response, create_json_response
from app.helpers.constants import MESSAGE_VALIDATION_ERROR_422
from app.helpers.custom_exceptions import CommonHTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.helpers.log_helper import get_logger

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with AsyncSessionLocal() as session:
            user = await ensure_default_user(session)
            logger.info(
                "Default user ready (postgres + chromadb): %s <%s>",
                user.name,
                user.email,
            )
    except Exception:
        logger.exception("Failed to ensure default user on startup")
        raise
    yield
    await pg_engine.dispose()


def configure_default_error_messages(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        errors = []
        for err in exc.errors():
            field_name = ".".join(map(str, err["loc"]))
            errors.append({"field": field_name, "error_message": err["msg"]})

        return create_json_error_response(MESSAGE_VALIDATION_ERROR_422, 422, errors)

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        errors = []
        for err in exc.errors():
            field_name = ".".join(map(str, err["loc"]))
            errors.append({"field": field_name, "error_message": err["msg"]})

        return create_json_error_response(MESSAGE_VALIDATION_ERROR_422, 422, errors)

    @app.exception_handler(CommonHTTPException)
    async def common_http_exception(request: Request, exc: CommonHTTPException):
        return create_json_response(exc.message, exc.status_code)


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://spinach.ddns.net",
    "http://spinach.ddns.net",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    api_v1_router,
    prefix="/api/v1",
    tags=[],
    # dependencies=[Depends(authenticate_api_key)],
)

configure_default_error_messages(app)
