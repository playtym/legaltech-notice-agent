"""Limitation period checker for Indian civil claims.

Uses Claude to determine claim category and applicable limitation
period. Falls back to keyword-based heuristics if LLM unavailable.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, timedelta
import re

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})\b",
    re.I,
)
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_SYSTEM_PROMPT = """\
You are an expert Indian civil law practitioner specialised in limitation periods. \
Given a consumer complaint, determine the claim category and applicable statutory \
limitation period.

LIMITATION PERIODS (Indian statutes):
- Consumer complaint (CPA 2019): 2 years from cause of action
- Contract breach (Limitation Act 1963, Art 55): 3 years
- Deficiency in service (CPA 2019): 2 years
- Product liability (CPA 2019 §59): 2 years
- Data breach / IT Act: 3 years (general tort)
- Payment disputes / banking: 3 years (PSS Act / general)
- Insurance claims (Insurance Act 1938): 3 years
- Unfair trade practice (CPA 2019): 2 years
- Real estate (RERA): 1 year from possession or 5 years for structural defect

Analyse the complaint facts and determine:
1. The most appropriate claim category
2. The statutory limitation period in years
3. Any special considerations (continuing cause of action, condonation, etc.)

Return JSON:
{
  "category": "descriptive category name",
  "limitation_years": integer,
  "statutory_basis": "Act and section reference",
  "special_notes": "any relevant considerations about limitation" or null
}

Return ONLY the JSON.
"""


@dataclass
class LimitationResult:
    earliest_event_date: date | None
    limitation_years: int
    deadline: date | None
    is_within_limit: bool
    days_remaining: int | None
    warning: str


# Fallback limitation periods
_LIMITATION_MAP: dict[str, int] = {
    "consumer_complaint": 2,
    "contract_breach": 3,
    "deficiency_service": 2,
    "product_liability": 2,
    "data_breach": 3,
    "payment_dispute": 3,
    "insurance_claim": 3,
    "unfair_trade_practice": 2,
}


def _detect_claim_category(corpus: str) -> str:
    lower = corpus.lower()
    if any(k in lower for k in ("product", "defective", "manufacturing", "goods")):
        return "product_liability"
    if any(k in lower for k in ("data", "privacy", "personal information", "leak")):
        return "data_breach"
    if any(k in lower for k in ("payment", "upi", "wallet", "transaction", "bank")):
        return "payment_dispute"
    if any(k in lower for k in ("insurance", "policy", "claim", "premium")):
        return "insurance_claim"
    if any(k in lower for k in ("contract", "agreement", "breach")):
        return "contract_breach"
    if any(k in lower for k in ("misleading", "false", "unfair", "hidden charge")):
        return "unfair_trade_practice"
    if any(k in lower for k in ("service", "delay", "support", "deficiency")):
        return "deficiency_service"
    return "consumer_complaint"


def _extract_earliest_date(timeline: list[str]) -> date | None:
    earliest: date | None = None
    for entry in timeline:
        match = _DATE_RE.search(entry)
        if match:
            day, month_str, year = match.groups()
            month = _MONTH_MAP.get(month_str[:3].lower(), 1)
            try:
                d = date(int(year), month, int(day))
            except ValueError:
                continue
            if earliest is None or d < earliest:
                earliest = d
    return earliest


def _build_result(category: str, years: int, earliest: date | None, today: date | None = None) -> LimitationResult:
    today = today or date.today()
    if earliest is None:
        return LimitationResult(
            earliest_event_date=None,
            limitation_years=years,
            deadline=None,
            is_within_limit=True,
            days_remaining=None,
            warning=(
                f"Cannot determine limitation period: no parseable date found in timeline. "
                f"Applicable limit for '{category}' claims is {years} years from cause of action. "
                f"Verify manually that the claim is not time-barred under the Limitation Act, 1963."
            ),
        )

    try:
        deadline = date(earliest.year + years, earliest.month, earliest.day)
    except ValueError:
        deadline = date(earliest.year + years, earliest.month, earliest.day - 1)

    days_remaining = (deadline - today).days
    is_within = days_remaining > 0

    if is_within and days_remaining < 90:
        warning = (
            f"URGENT: Only {days_remaining} days remain before limitation expires on {deadline.isoformat()}. "
            f"Claim category: '{category}' ({years}-year limit). File notice and escalate immediately."
        )
    elif is_within:
        warning = (
            f"Claim is within limitation period. Deadline: {deadline.isoformat()} "
            f"({days_remaining} days remaining). Claim category: '{category}' ({years}-year limit)."
        )
    else:
        warning = (
            f"CLAIM LIKELY TIME-BARRED. Limitation expired on {deadline.isoformat()} "
            f"({abs(days_remaining)} days ago). Claim category: '{category}' ({years}-year limit). "
            f"Notice may be unenforceable. Consult an advocate for potential exception "
            f"(e.g. Section 5 Limitation Act — condonation of delay)."
        )

    return LimitationResult(
        earliest_event_date=earliest,
        limitation_years=years,
        deadline=deadline,
        is_within_limit=is_within,
        days_remaining=days_remaining if is_within else None,
        warning=warning,
    )


def check_limitation(timeline: list[str], issue_summary: str, today: date | None = None) -> LimitationResult:
    """Deterministic fallback."""
    category = _detect_claim_category(issue_summary)
    years = _LIMITATION_MAP.get(category, 2)
    earliest = _extract_earliest_date(timeline)
    return _build_result(category, years, earliest, today)


class LimitationAgent:
    """LLM-powered limitation period analysis with deterministic fallback."""

    def __init__(self, llm=None) -> None:
        self.llm = llm

    async def run(self, timeline: list[str], issue_summary: str, today: date | None = None) -> LimitationResult:
        earliest = _extract_earliest_date(timeline)
        today = today or date.today()

        if self.llm:
            try:
                return await self._agentic_run(issue_summary, timeline, earliest, today)
            except Exception as exc:
                logger.warning("LLM limitation analysis failed, using fallback: %s", exc)
        return check_limitation(timeline, issue_summary, today)

    async def _agentic_run(
        self, issue_summary: str, timeline: list[str], earliest: date | None, today: date
    ) -> LimitationResult:
        timeline_text = "\n".join(f"- {t}" for t in timeline) if timeline else "(no timeline)"
        user_prompt = (
            f"## Issue Summary\n{issue_summary}\n\n"
            f"## Timeline\n{timeline_text}\n\n"
            f"## Earliest detected date: {earliest.isoformat() if earliest else 'not detected'}\n"
            f"## Today: {today.isoformat()}"
        )
        data = await self.llm.complete_json(_SYSTEM_PROMPT, user_prompt)
        category = data.get("category", "consumer_complaint")
        years = int(data.get("limitation_years", 2))
        return _build_result(category, years, earliest, today)
