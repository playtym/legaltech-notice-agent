"""Claude-powered LLM service via Amazon Bedrock (or direct Anthropic API).

Model: claude-sonnet-4-20250514 via Bedrock inference profile
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-20250514"
_FAST_MODEL = "claude-3-haiku-20240307"
_FAST_MODEL_MAX_TOKENS = 4096
_BEDROCK_MODEL = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
_BEDROCK_FAST_MODEL = "apac.anthropic.claude-3-5-haiku-20241022-v1:0"
_MAX_TOKENS = 8192


class LLMService:
    """Thin wrapper around Anthropic Messages API (Bedrock or direct)."""

    def __init__(self, model_name: str = _DEFAULT_MODEL, api_key: str | None = None) -> None:
        use_bedrock = os.getenv("USE_BEDROCK", "").lower() in ("1", "true", "yes")
        aws_region = os.getenv("AWS_REGION", "ap-south-1")
        self._max_output_tokens: int | None = None

        if use_bedrock:
            self.model_name = os.getenv("BEDROCK_MODEL_ID", _BEDROCK_MODEL)
            self.client = anthropic.AsyncAnthropicBedrock(aws_region=aws_region)
            logger.info("LLM: using Bedrock in %s, model=%s", aws_region, self.model_name)
        else:
            self.model_name = model_name or _DEFAULT_MODEL
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
            logger.info("LLM: using direct Anthropic API, model=%s", self.model_name)

    def fast_copy(self, fast_model: str | None = None) -> "LLMService":
        """Create a sibling instance using a faster/cheaper model, sharing the same client."""
        use_bedrock = os.getenv("USE_BEDROCK", "").lower() in ("1", "true", "yes")
        clone = object.__new__(LLMService)
        clone.client = self.client  # reuse connection pool
        if use_bedrock:
            clone.model_name = fast_model or os.getenv("BEDROCK_FAST_MODEL_ID", _BEDROCK_FAST_MODEL)
        else:
            clone.model_name = fast_model or _FAST_MODEL
        clone._max_output_tokens = _FAST_MODEL_MAX_TOKENS
        logger.info("LLM fast: model=%s (max_tokens=%d)", clone.model_name, clone._max_output_tokens)
        return clone

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = _MAX_TOKENS,
    ) -> dict[str, Any]:
        """Call Claude and parse the response as JSON."""
        text = await self.complete_text(system_prompt, user_prompt, max_tokens)
        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            first_nl = cleaned.index("\n")
            last_fence = cleaned.rfind("```")
            cleaned = cleaned[first_nl + 1 : last_fence].strip()
        return json.loads(cleaned)

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = _MAX_TOKENS,
    ) -> str:
        """Call Claude and return plain text."""
        if self._max_output_tokens:
            max_tokens = min(max_tokens, self._max_output_tokens)
        message = await self.client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    @property
    def pricing_info(self) -> dict[str, Any]:
        return {
            "model": self.model_name,
            "input_per_million_tokens_usd": 3.0,
            "output_per_million_tokens_usd": 15.0,
            "estimated_tokens_per_generation": {
                "input": 8_000,
                "output": 5_000,
            },
            "estimated_cost_per_generation_usd": round(
                (8_000 * 3.0 / 1_000_000) + (5_000 * 15.0 / 1_000_000), 4
            ),
        }


def to_pretty_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True)
