# patched for compat
SettingsConfigDict = None
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
except Exception:
    from pydantic import BaseSettings  # type: ignore
from functools import lru_cache
from typing import Optional
import os

class Settings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None
    DEFAULT_MODEL: str = "gpt-4o-mini"
    # Pydantic v2 (pydantic-settings) usa model_config; si no, fallback a Config
    if 'SettingsConfigDict' in globals() and SettingsConfigDict is not None:  # type: ignore
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")  # type: ignore
    else:
        class Config:  # type: ignore
            env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()


API_VERSION = "v1"
DATA_DIR = os.getenv("DATA_DIR", "./storage")
MININODE_API_KEY = os.getenv("MININODE_API_KEY", "")
# MININODE_API_KEY = os.getenv("MININODE_API_KEY", "")  # ya lo tienes; si no, aÃ±Ã¡delo

