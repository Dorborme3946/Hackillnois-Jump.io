from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    supermemory_api_key: str = ""
    upload_dir: str = "/tmp/jumpai_uploads"
    max_upload_size_mb: int = 500

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
