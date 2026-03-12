from functools import lru_cache
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    model_name: str = Field(default=os.getenv("MODEL_NAME", "claude-sonnet-4-20250514"))
    anthropic_api_key: str | None = Field(default=os.getenv("ANTHROPIC_API_KEY"))
    request_timeout_seconds: int = Field(default=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")))
    user_agent: str = Field(
        default=os.getenv(
            "LEGALTECH_USER_AGENT",
            "LegalTech-Notice-Agent/0.1 (+https://example.com)",
        )
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
