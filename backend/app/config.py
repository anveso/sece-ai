"""
Centralized application settings, loaded from environment variables / .env.

Every other module should import `settings` from here instead of reading
os.environ directly, so all configuration stays discoverable in one place.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_name: str = "SECE AI"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    # --- Database ---
    database_url: str = "postgresql+psycopg2://sece:sece_dev_password@db:5432/sece_ai"

    # --- Auth ---
    jwt_secret: str = "change-this-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # --- LLM ---
    openai_api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # --- Web search tool (optional) ---
    tavily_api_key: str = ""

    # --- Storage ---
    upload_dir: str = "/data/uploads"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
