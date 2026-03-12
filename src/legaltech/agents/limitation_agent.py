"""Limitation period checker for Indian civil claims.

Validates whether the complaint is within the statutory limitation
period before allowing notice generation. A time-barred claim is
legally unenforceable and a notice based on it is wasteful.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import re

_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})\b",
    re.I,
)
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


@dataclass
class LimitationResult:
    earliest_event_date: date | None
    limitation_years: int
    deadline: date | None
    is_within_limit: bool
    days_remaining: int | None
    warning: str


# Limitation periods by claim category (Limitation Act, 1963 + CPA 2019)
_LIMITATION_MAP: dict[str, int] = {
    "consumer_complaint": 2,        # CPA 2019 - from date cause of action arose
    "contract_breach": 3,           # Limitation Act, Schedule I, Art 55
    "deficiency_service": 2,        # CPA 2019
    "product_liability": 2,         # CPA 2019 §59 read with Schedule
    "data_breach": 3,               # IT Act / general tort — 3 years
    "payment_dispute": 3,           # Banking / PSS Act — general
    "insurance_claim": 3,           # Insurance Act, 1938
    "unfair_trade_practice": 2,     # CPA 2019
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


def check_limitation(
    timeline: list[str],
    issue_summary: str,
    today: date | None = None,
) -> LimitationResult:
    today = today or date.today()
    category = _detect_claim_category(issue_summary)
    years = _LIMITATION_MAP.get(category, 2)

    earliest = _extract_earliest_date(timeline)

    if earliest is None:
        return LimitationResult(
            earliest_event_date=None,
            limitation_years=years,
            deadline=None,
            is_within_limit=True,  # can't determine — let it through with warning
            days_remaining=None,
            warning=(
                f"Cannot determine limitation period: no parseable date found in timeline. "
                f"Applicable limit for '{category}' claims is {years} years from cause of action. "
                f"Verify manually that the claim is not time-barred under the Limitation Act, 1963."
            ),
        )

    deadline = date(earliest.year + years, earliest.month, earliest.day)
    try:
        deadline = date(earliest.year + years, earliest.month, earliest.day)
    except ValueError:
        # leap-year edge case
        deadline = date(earliest.year + years, earliest.month, earliest.day - 1)

    days_remaining = (deadline - today).days
    is_within = days_remaining > 0

    if is_within and days_remaining < 90:
        warning = (
            f"URGENT: Only {days_remaining} days remain before limitation expires on {deadline.isoformat()}. "
            f"Claim category: '{category}' ({years}-year limit under Limitation Act, 1963). "
            f"File notice and escalate immediately."
        )
    elif is_within:
        warning = (
            f"Claim is within limitation period. Deadline: {deadline.isoformat()} "
            f"({days_remaining} days remaining). "
            f"Claim category: '{category}' ({years}-year limit)."
        )
    else:
        warning = (
            f"CLAIM LIKELY TIME-BARRED. Limitation expired on {deadline.isoformat()} "
            f"({abs(days_remaining)} days ago). "
            f"Claim category: '{category}' ({years}-year limit under Limitation Act, 1963). "
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
