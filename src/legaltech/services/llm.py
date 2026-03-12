"""Claude-powered LLM service via Anthropic API.

Model: claude-sonnet-4-20250514
Pricing (per million tokens): Input $3 | Output $15
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-20250514"
_MAX_TOKENS = 8192


class LLMService:
    """Thin wrapper around Anthropic Messages API."""

    def __init__(self, model_name: str = _DEFAULT_MODEL, api_key: str | None = None) -> None:
        self.model_name = model_name or _DEFAULT_MODEL
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

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
