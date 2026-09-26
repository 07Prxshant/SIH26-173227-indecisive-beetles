"""Environment-backed application configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime settings read from environment variables and the repository .env file."""

    service_name: str = "urban-sense-backend"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    database_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("URBANSENSE_DATABASE_URL", "DATABASE_URL"),
    )
    postgres_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("URBANSENSE_POSTGRES_HOST", "POSTGRES_HOST"),
    )
    postgres_port: int = Field(
        default=5432,
        validation_alias=AliasChoices("URBANSENSE_POSTGRES_PORT", "POSTGRES_PORT"),
    )
    postgres_db: str = Field(
        default="urbansense",
        validation_alias=AliasChoices("URBANSENSE_POSTGRES_DB", "POSTGRES_DB"),
    )
    postgres_user: str = Field(
        default="urbansense",
        validation_alias=AliasChoices("URBANSENSE_POSTGRES_USER", "POSTGRES_USER"),
    )
    postgres_password: str = Field(
        default="change-me",
        validation_alias=AliasChoices("URBANSENSE_POSTGRES_PASSWORD", "POSTGRES_PASSWORD"),
    )

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_prefix="URBANSENSE_",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        """Return an explicit database URL or compose one from PostgreSQL settings."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
