from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FlowForge"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://flowforge:flowforge@postgres:5432/flowforge"
    test_database_url: str = "sqlite+pysqlite:///:memory:"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    cors_origins: str = "http://localhost:3000,http://frontend:3000"
    openai_api_key: str | None = None
    rate_limit: str = "120/minute"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
