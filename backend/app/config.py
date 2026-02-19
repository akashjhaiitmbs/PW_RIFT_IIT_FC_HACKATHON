from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/pharmaguard"

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION: str = "cpic_guidelines"

    # ── Azure OpenAI / OpenAI SDK settings ───────────────────────────────────
    OPENAI_API_TYPE: str = "azure"           # "azure" | "openai"

    # Azure OpenAI — fill these from your Azure portal
    AZURE_OPENAI_ENDPOINT: str = "https://your-resource.openai.azure.com/"
    AZURE_OPENAI_API_KEY: str = "your-azure-api-key-here"
    AZURE_OPENAI_API_VERSION: str = "2025-01-01-preview"
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-5"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"

    # Plain OpenAI fallback (only used when OPENAI_API_TYPE="openai")
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
