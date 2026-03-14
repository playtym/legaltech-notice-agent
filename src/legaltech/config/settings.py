from functools import lru_cache
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    model_name: str = Field(default=os.getenv("MODEL_NAME", "claude-sonnet-4-20250514"))
    fast_model_name: str = Field(default=os.getenv("FAST_MODEL_NAME", "claude-3-haiku-20240307"))
    anthropic_api_key: str | None = Field(default=os.getenv("ANTHROPIC_API_KEY"))
    use_bedrock: bool = Field(default=os.getenv("USE_BEDROCK", "").lower() in ("1", "true", "yes"))
    request_timeout_seconds: int = Field(default=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")))
    user_agent: str = Field(
        default=os.getenv(
            "LEGALTECH_USER_AGENT",
            "Lawly/0.2 (+https://lawly.store)",
        )
    )
    admin_password: str = Field(default=os.getenv("ADMIN_PASSWORD", "lawly2024"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
