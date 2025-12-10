"""
Application configuration settings
"""

import os
from typing import Any, Literal, cast

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def coerce_comma_separated_to_list(v: Any, *, filter_empty: bool = False) -> Any:
    """
    Coerce values that may be a comma-separated string or list into a list.
    - If v is a non-JSON-looking string (doesn't start with '['), split by comma and strip items.
    - If v is already a list or a string (e.g., JSON array string), return as-is.
    - Optionally filter out empty items after stripping.
    """
    if isinstance(v, str) and not v.startswith("["):
        items = [i.strip() for i in v.split(",")]
        if filter_empty:
            items = [i for i in items if i]
        return items
    if isinstance(v, (list, str)):
        return cast(Any, v)
    raise ValueError(f"Invalid type for list coercion: {type(v)}")


class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    PROJECT_NAME: str = "Aurorah API Server"
    DESCRIPTION: str = "Aurorah API Server - FastAPI REST API for the Aurorah System"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 33001

    # CORS Configuration
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://hm-aurorah-api",
        "http://hm-aurorah-api:3000",
        "http://dev.aurorah.ai",
        "https://dev.aurorah.ai",
        "http://aurorah.ai",
        "https://aurorah.ai",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        try:
            return coerce_comma_separated_to_list(v)
        except ValueError:
            raise ValueError(f"Invalid type for CORS origins: {type(v)}")

    # API Key Configuration (up to 100 keys: API_KEY1 to API_KEY99)
    # Format: name,enabled,type,key (e.g., "hm-aurorah-web-1,true,user,a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6").
    # Example: API_KEY1="hm-aurorah-web-1,true,admin,a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    # api_keys will be:
    # api_keys = {
    #   "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6": {"name": "hm-aurorah-web-1", "enabled": True, "type": "user"}
    # }
    api_keys: dict[str, dict[str, str | bool | Literal["user", "admin"]]] = {}

    @model_validator(mode="before")
    @classmethod
    def parse_api_keys(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Parse API_KEY1 through API_KEY99 from environment variables"""

        api_keys = {}
        for i in range(1, 100):
            key_name = f"API_KEY{i}"
            # Read directly from os.environ first, then fallback to values
            raw_value = os.environ.get(key_name) or values.get(key_name)
            if raw_value:
                parts = [p.strip() for p in raw_value.split(",")]
                if len(parts) == 4:
                    name, enabled_str, type, key = parts
                    enabled = enabled_str.lower() in ("true", "1", "yes")
                    # Use the key value as the dict key for fast lookup
                    api_keys[key] = {
                        "name": name,
                        "enabled": enabled,
                        "type": type.lower(),  # "user" or "admin"
                    }
        values["api_keys"] = api_keys
        return values

    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "aurorah"
    POSTGRES_URL: str | None = None

    @property
    def postgres_url(self) -> str:
        """Construct database URL"""
        if self.POSTGRES_URL:
            return self.POSTGRES_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_URL: str | None = None

    # Redis Stream Message Queue Maxlen: 1 million messages (1M * 5 characters * 2 bytes = 10MB --> Maximum allowed textbook size)
    REDIS_STREAM_MQ_MAXLEN: int = 1_000_000
    # Redis Stream Message Queue TTL Seconds: 1 hour for development, 5 minutes for production (to prevent memory leak)
    REDIS_STREAM_MQ_TTL_SECONDS: int = 3600 if ENVIRONMENT == "development" else 300

    @property
    def redis_url(self) -> str:
        """Construct Redis URL"""
        if self.REDIS_URL:
            return self.REDIS_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Security Configuration
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # AI Integration Settings
    OPENAI_API_KEY: str | None = None
    LANGSMITH_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None

    # External Services
    LANGGRAPH_API_URL: str = "http://localhost:8123"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
