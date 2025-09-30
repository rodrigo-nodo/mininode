from pydantic import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    OPENAI_API_KEY: str | None = None
    DEFAULT_MODEL: str = "gpt-4o-mini"
    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
