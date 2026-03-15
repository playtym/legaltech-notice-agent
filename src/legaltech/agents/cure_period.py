"""Dynamic cure period determination.

Uses Claude to assess dispute complexity and determine an appropriate
cure period. Falls back to keyword-based heuristics if LLM unavailable.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert Indian consumer law practitioner. Given a consumer complaint, \
determine the appropriate cure period (number of days the company should be given \
to resolve the issue before the consumer escalates to legal action).

GUIDELINES (Indian norms):
- Unauthorized financial transactions: 7 days (RBI zero-liability timeline)
- UPI/IMPS failed transactions: 5 business days (RBI TAT circular — T+5 auto-reversal)
- Simple refunds / payment reversals: 15 days (e-commerce + RBI norms)
- Delivery issues / service deficiency: 15 days
- Product defects requiring inspection/replacement: 21 days
- Insurance claim settlement: 30 days from last document (IRDAI Reg 17(6))
- Data breaches / privacy violations: 30 days (IT Act / DPDP Act)
- Complex disputes with long history: 30 days
- Life/safety threatening issues: 7 days
- Airline refund (domestic cancellation): 14 days (DGCA norm)
- Ed-tech refund / course cancellation: 15 days
- Builder/RERA delay: 30 days (but interest runs from original date)
- Credit score dispute by CIC: 30 days (CICRA §15 timeline)
- Dark pattern complaints: 15 days
- Expired/unsafe food: 7 days (health/safety urgency)

Consider:
- Urgency of the consumer's situation
- Complexity of the resolution required
- Industry norms and regulatory timelines
- Whether the company has already been given time to respond

Return JSON:
{
  "cure_days": integer (5, 7, 14, 15, 21, or 30),
  "rationale": "brief explanation of why this period is appropriate",
  "urgency": "low|medium|high|critical"
}

Return ONLY the JSON.
"""


def determine_cure_period(issue_summary: str, timeline_length: int) -> tuple[int, str]:
    """Deterministic fallback: keyword-based cure period."""
    lower = issue_summary.lower()

    if any(k in lower for k in ("unauthorized transaction", "fraud", "hacked", "stolen")):
        return 7, "7 days (urgent — unauthorized financial transaction per RBI circular on zero-liability timeline)"
    if any(k in lower for k in ("upi failed", "upi deducted", "payment failed but debited", "auto reversal", "t+5",
                                "amount deducted but not credited", "transaction failed but debited")):
        return 5, "5 business days (RBI mandated T+5 auto-reversal for UPI/IMPS failed transactions — ₹100/day penalty thereafter)"
    if any(k in lower for k in ("expired food", "contaminated food", "food poisoning", "stale food",
                                "rotten", "insect in food", "unsafe food")):
        return 7, "7 days (health/safety urgency — unsafe food under FSSA 2006)"
    if any(k in lower for k in ("flight cancel", "flight delay", "airline refund", "denied boarding",
                                "airline compensation")):
        return 14, "14 days (DGCA standard refund/compensation processing timeline)"
    if any(k in lower for k in ("edtech", "ed-tech", "course refund", "placement guarantee",
                                "coaching refund", "byju", "unacademy")):
        return 15, "15 days (ed-tech refund per E-Commerce Rules 2020 and CPA 2019)"
    if any(k in lower for k in ("dark pattern", "subscription trap", "basket sneaking",
                                "forced action", "auto renew")):
        return 15, "15 days (dark pattern complaint — CCPA Guidelines 2023)"
    if any(k in lower for k in ("claim rejected", "claim denied", "insurance rejected",
                                "insurance claim", "irdai", "mediclaim")):
        return 30, "30 days (IRDAI mandated settlement timeline per Regulation 17(6) — interest at bank rate + 2% for delay)"
    if any(k in lower for k in ("credit score", "cibil", "credit report", "wrong credit")):
        return 30, "30 days (statutory dispute resolution timeline per CICRA 2005 §15)"
    if any(k in lower for k in ("rera", "builder delay", "delayed possession", "possession date")):
        return 30, "30 days (RERA compliance notice — interest runs from original promised date regardless)"
    if any(k in lower for k in ("refund", "payment failed", "double charged", "overcharged")):
        return 15, "15 days (standard refund/payment reversal per RBI and e-commerce norms)"
    if any(k in lower for k in ("not delivered", "delivery", "deficiency")):
        return 15, "15 days (standard service resolution period)"
    if any(k in lower for k in ("defective", "damaged", "faulty", "replacement", "repair")):
        return 21, "21 days (reasonable period for product inspection and replacement logistics)"
    if any(k in lower for k in ("data leak", "privacy", "personal data", "security breach")):
        return 30, "30 days (per IT Act reasonable security practices timeline and DPDP Act notification period)"
    if timeline_length >= 5:
        return 30, "30 days (complex dispute with extended history requiring internal review)"
    return 15, "15 days (standard consumer grievance resolution period)"


class CurePeriodAgent:
    """Determines appropriate cure period using LLM reasoning with deterministic fallback."""

    def __init__(self, llm=None) -> None:
        self.llm = llm

    async def run(self, issue_summary: str, timeline_length: int, timeline: list[str] | None = None) -> tuple[int, str]:
        if self.llm:
            try:
                return await self._agentic_run(issue_summary, timeline_length, timeline)
            except Exception as exc:
                logger.warning("LLM cure period failed, using fallback: %s", exc)
        return determine_cure_period(issue_summary, timeline_length)

    async def _agentic_run(
        self, issue_summary: str, timeline_length: int, timeline: list[str] | None
    ) -> tuple[int, str]:
        timeline_text = "\n".join(f"- {t}" for t in (timeline or [])) if timeline else f"({timeline_length} events)"
        user_prompt = (
            f"## Issue Summary\n{issue_summary}\n\n"
            f"## Timeline ({timeline_length} events)\n{timeline_text}"
        )
        data = await self.llm.complete_json(_SYSTEM_PROMPT, user_prompt)
        days = int(data["cure_days"])
        rationale = data["rationale"]
        return days, f"{days} days ({rationale})"
