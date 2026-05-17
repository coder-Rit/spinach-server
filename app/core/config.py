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

    CHROMA_COLLECTION_NAME: str

    JWT_SECRET_KEY: str = "change-me-please-set-a-strong-secret"
    JWT_ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    default_user_name: str = "John Doe"
    default_user_email: str = "john.doe@spinach.ddns.net"
    default_user_password: str = "johndoe123"

    OPENAI_MODEL:str =""
    OPENROUTER_MODEL:str =""
    NVIDIA_MODEL:str =""
    GEMINI_MODEL: str = ""
    GEMINI_API_KEY_1: str = ""
    GEMINI_API_KEY_2: str = ""
    GEMINI_API_KEY_3: str = ""
    GEMINI_API_KEY_4: str = ""
    GEMINI_API_KEY_5: str = ""

    @computed_field  # type: ignore[misc]
    @property
    def gemini_api_keys(self) -> list[str]:
        """Non-empty Gemini keys from GEMINI_API_KEY_1 … GEMINI_API_KEY_5."""
        raw = (
            self.GEMINI_API_KEY_1,
            self.GEMINI_API_KEY_2,
            self.GEMINI_API_KEY_3,
            self.GEMINI_API_KEY_4,
            self.GEMINI_API_KEY_5,
        )
        return [k.strip() for k in raw if k and k.strip()]

    @computed_field  # type: ignore[misc]
    @property
    def database_uri(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
