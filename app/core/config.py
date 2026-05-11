from dotenv import load_dotenv
from pydantic import computed_field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    app_name: str = "Palak Backend"
    environment: str = "prod"
    OPENROUTER_API_KEY: str = ""
    APP_PORT: int = 8000

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "spinach_1"

    JWT_SECRET_KEY: str = "change-me-please-set-a-strong-secret"
    JWT_ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    @computed_field  # type: ignore[misc]
    @property
    def database_uri(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
