"""Application configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_HOST: str = Field(default="0.0.0.0", description="API host bind address")
    API_PORT: int = Field(default=8000, description="API port")
    API_ENV: str = Field(default="development", description="Application environment")
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/recoverai",
        description="PostgreSQL async database connection URL",
    )


settings = Settings()
