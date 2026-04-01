"""Claude-powered LLM service via Amazon Bedrock (or direct Anthropic API).

Model: claude-sonnet-4-20250514 via Bedrock inference profile
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import anthropic
import httpx

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-20250514"
_FAST_MODEL = "claude-3-haiku-20240307"
_FAST_MODEL_MAX_TOKENS = 4096
_BEDROCK_MODEL = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
_BEDROCK_FAST_MODEL = "apac.anthropic.claude-3-5-haiku-20241022-v1:0"
_MAX_TOKENS = 8192

_MAX_RETRIES = 2
_RETRY_BASE_DELAY = 1.0  # seconds — exponential backoff: 1s, 2s
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 529}


def _strip_code_fences(text: str) -> str:
    """Robustly strip markdown code fences from LLM output."""
    s = text.strip()
    # Pattern: ```json ... ``` or ```\n ... ```
    m = re.match(r'^```(?:\w*)\s*\n(.*?)```\s*$', s, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Fallback: starts with ``` but maybe no closing
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl == -1:
            return s[3:].strip()
        last_fence = s.rfind("```", first_nl)
        if last_fence > first_nl:
            return s[first_nl + 1:last_fence].strip()
        return s[first_nl + 1:].strip()
    return s


class LLMService:
    """Thin wrapper around Anthropic Messages API (Bedrock or direct)."""

    def __init__(self, model_name: str = _DEFAULT_MODEL, api_key: str | None = None) -> None:
        use_bedrock = os.getenv("USE_BEDROCK", "").lower() in ("1", "true", "yes")
        aws_region = os.getenv("AWS_REGION", "ap-south-1")
        self._max_output_tokens: int | None = None

        if use_bedrock:
            self.model_name = os.getenv("BEDROCK_MODEL_ID", _BEDROCK_MODEL)
            self.client = anthropic.AsyncAnthropicBedrock(
                aws_region=aws_region,
                timeout=httpx.Timeout(60.0, connect=10.0),
                max_retries=0,  # we handle retries ourselves
            )
            logger.info("LLM: using Bedrock in %s, model=%s", aws_region, self.model_name)
        else:
            self.model_name = model_name or _DEFAULT_MODEL
            self.client = anthropic.AsyncAnthropic(
                api_key=api_key,
                timeout=httpx.Timeout(60.0, connect=10.0),
                max_retries=0,
            )
            logger.info("LLM: using direct Anthropic API, model=%s", self.model_name)

    def fast_copy(self, fast_model: str | None = None) -> "LLMService":
        """Create a sibling instance using a faster/cheaper model, sharing the same client."""
        use_bedrock = os.getenv("USE_BEDROCK", "").lower() in ("1", "true", "yes")
        clone = object.__new__(LLMService)
        clone.client = self.client  # reuse connection pool
        if use_bedrock:
            # Ignore any fast_model that looks like a direct-API ID (no dots/colons = wrong format)
            bedrock_override = fast_model if fast_model and ("." in fast_model or ":" in fast_model) else None
            clone.model_name = bedrock_override or os.getenv("BEDROCK_FAST_MODEL_ID", _BEDROCK_FAST_MODEL)
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
        """Call Claude and parse the response as JSON, with retry on parse failure."""
        last_err: Exception | None = None
        for attempt in range(2):  # one retry on JSON parse failure
            text = await self.complete_text(system_prompt, user_prompt, max_tokens)
            cleaned = _strip_code_fences(text)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                last_err = e
                logger.warning(
                    "LLM JSON parse failed (attempt %d): %s — raw: %.200s",
                    attempt + 1, e, text,
                )
                if attempt == 0:
                    # Retry with an explicit "output valid JSON" nudge
                    user_prompt = (
                        user_prompt
                        + "\n\nIMPORTANT: Your previous response was not valid JSON. "
                        "Please respond with ONLY a valid JSON object, no markdown fences or extra text."
                    )
        raise ValueError(f"LLM returned invalid JSON after 2 attempts: {last_err}")

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = _MAX_TOKENS,
    ) -> str:
        """Call Claude and return plain text, with automatic retry on transient errors."""
        if self._max_output_tokens:
            max_tokens = min(max_tokens, self._max_output_tokens)

        last_err: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                message = await self.client.messages.create(
                    model=self.model_name,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                if not message.content:
                    raise ValueError("Claude returned empty content (possible content filter)")
                return message.content[0].text
            except anthropic.APIStatusError as e:
                last_err = e
                if e.status_code in _RETRYABLE_STATUS_CODES:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "LLM API error %d (attempt %d/%d), retrying in %.1fs: %s",
                        e.status_code, attempt + 1, _MAX_RETRIES, delay, e.message,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise  # non-retryable status (400, 401, etc.)
            except (anthropic.APIConnectionError, httpx.TimeoutException) as e:
                last_err = e
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "LLM connection/timeout error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, _MAX_RETRIES, delay, e,
                )
                await asyncio.sleep(delay)
                continue
        raise last_err  # type: ignore[misc]

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
