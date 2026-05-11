from fastapi import APIRouter

from app.api.v1.llm import chat_router
from app.api.v1.auth import auth_router
from app.api.v1.user import user_router
from app.api.v1.projects import projects_router
from app.api.v1.work_items import work_items_router
from app.api.v1.comments import comments_router
from app.api.v1.chats import chats_router

api_v1_router = APIRouter()



api_v1_router.include_router(
    chat_router,
    tags=["Chat Router"],
)


api_v1_router.include_router(auth_router)
api_v1_router.include_router(user_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(work_items_router)
api_v1_router.include_router(comments_router)
api_v1_router.include_router(chats_router)


