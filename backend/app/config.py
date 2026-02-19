from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/pharmaguard"
    REDIS_URL: str = "redis://localhost:6379/0"

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "cpic_guidelines"

    LLM_ENDPOINT: str = "http://localhost:11434/api/generate"
    LLM_MODEL: str = "biomistral"

    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
