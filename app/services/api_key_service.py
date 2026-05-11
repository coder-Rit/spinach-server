from sqlalchemy.ext.asyncio import AsyncSession
from app.models.api_keys import ApiKeysModel
from app.services.base_service import BaseService


class ApiKeyService(BaseService[ApiKeysModel]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ApiKeysModel)
