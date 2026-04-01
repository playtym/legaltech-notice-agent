from functools import lru_cache
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    model_name: str = Field(default=os.getenv("MODEL_NAME", "claude-sonnet-4-20250514"))
    fast_model_name: str | None = Field(default=os.getenv("FAST_MODEL_NAME") or None)
    anthropic_api_key: str | None = Field(default=os.getenv("ANTHROPIC_API_KEY"))
    use_bedrock: bool = Field(default=os.getenv("USE_BEDROCK", "").lower() in ("1", "true", "yes"))
    request_timeout_seconds: int = Field(default=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")))
    user_agent: str = Field(
        default=os.getenv(
            "LEGALTECH_USER_AGENT",
            "Lawly/0.2 (+https://lawly.store)",
        )
    )
    admin_password: str = Field(default=os.getenv("ADMIN_PASSWORD", ""))
    data_bucket: str | None = Field(default=os.getenv("DATA_BUCKET"))
    bing_webmaster_api_key: str | None = Field(default=os.getenv("BING_WEBMASTER_API_KEY"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    if not s.admin_password:
        import logging
        logging.getLogger(__name__).warning(
            "ADMIN_PASSWORD is not set — admin login is disabled until configured"
        )
    return s
