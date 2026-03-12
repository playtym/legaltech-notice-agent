"""Evidence consistency scoring and contradiction detection.

Uses Claude to contextually assess evidence quality, detect contradictions,
and suggest improvements. Falls back to keyword heuristics if LLM unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from legaltech.schemas import ComplaintInput

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a senior Indian consumer law evidence analyst. Assess the quality of evidence \
provided in a consumer complaint for legal notice purposes.

Evaluate:
1. COMPLETENESS — Does the consumer have key evidence types? (receipt/invoice, order ID, \
   payment proof, communication records, screenshots)
2. CONSISTENCY — Are the facts, dates, and amounts internally consistent?
3. CONTRADICTIONS — Any contradictory claims or amount discrepancies?
4. GAPS — What critical evidence is missing that would strengthen the case?

Return JSON:
{
  "overall_score": 0.0 to 1.0,
  "completeness_score": 0.0 to 1.0,
  "consistency_score": 0.0 to 1.0,
  "contradictions": ["list of contradictions found"],
  "gaps": ["list of evidence gaps"],
  "suggestions": ["actionable suggestions to strengthen evidence"]
}

Score generously for implicit evidence (e.g., mentioning an order implies a receipt exists).
Return ONLY the JSON.
"""

_DATE_RE = re.compile(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})\b", re.I)
_AMOUNT_RE = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)", re.I)


@dataclass
class EvidenceScore:
    overall_score: float = 0.0
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    contradictions: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class EvidenceScoringAgent:
    """Scores evidence quality, detects contradictions, and suggests improvements."""

    def __init__(self, llm=None) -> None:
        self.llm = llm

    async def run(self, complaint: ComplaintInput, normalized_issue: str) -> EvidenceScore:
        if self.llm:
            try:
                return await self._agentic_run(complaint, normalized_issue)
            except Exception as exc:
                logger.warning("LLM evidence scoring failed, using fallback: %s", exc)
        return self._deterministic_run(complaint, normalized_issue)

    async def _agentic_run(self, complaint: ComplaintInput, normalized_issue: str) -> EvidenceScore:
        user_prompt = (
            f"## Normalized Issue\n{normalized_issue}\n\n"
            f"## Timeline ({len(complaint.timeline)} entries)\n"
            + "\n".join(f"- {t}" for t in complaint.timeline) + "\n\n"
            f"## Evidence ({len(complaint.evidence)} items)\n"
            + "\n".join(f"- {e}" for e in complaint.evidence) + "\n\n"
            f"## Desired Resolution\n{complaint.desired_resolution}"
        )
        data = await self.llm.complete_json(_SYSTEM_PROMPT, user_prompt)
        return EvidenceScore(
            overall_score=round(float(data.get("overall_score", 0.5)), 2),
            completeness_score=round(float(data.get("completeness_score", 0.5)), 2),
            consistency_score=round(float(data.get("consistency_score", 0.8)), 2),
            contradictions=data.get("contradictions", []),
            gaps=data.get("gaps", []),
            suggestions=data.get("suggestions", []),
        )

    def _deterministic_run(self, complaint: ComplaintInput, normalized_issue: str) -> EvidenceScore:
        result = EvidenceScore()
        expected_types = {
            "receipt_or_invoice": ("invoice", "receipt", "bill", "order"),
            "order_id": ("order number", "order id", "order #", "reference"),
            "payment_proof": ("payment", "transaction", "upi", "bank", "card", "wallet"),
            "communication": ("email", "chat", "ticket", "call", "sms", "whatsapp"),
            "screenshot": ("screenshot", "photo", "image", "attachment"),
        }
        corpus = " ".join([
            normalized_issue, " ".join(complaint.evidence), " ".join(complaint.timeline),
        ]).lower()

        found_types = 0
        for etype, keywords in expected_types.items():
            if any(k in corpus for k in keywords):
                found_types += 1
            else:
                result.gaps.append(f"Missing evidence type: {etype.replace('_', ' ')}")
        result.completeness_score = round(found_types / len(expected_types), 2)

        timeline_dates = _extract_dates(complaint.timeline)
        consistency_issues = 0
        if len(timeline_dates) >= 2:
            for i in range(1, len(timeline_dates)):
                if timeline_dates[i] < timeline_dates[i - 1]:
                    result.contradictions.append(f"Timeline order issue: entry {i + 1} date before entry {i}")
                    consistency_issues += 1

        amounts_in_issue = _extract_amounts(normalized_issue)
        amounts_in_evidence = _extract_amounts(" ".join(complaint.evidence))
        all_amounts = set(amounts_in_issue + amounts_in_evidence)
        if len(all_amounts) > 1:
            sorted_amounts = sorted(all_amounts)
            if sorted_amounts[-1] > sorted_amounts[0] * 10:
                result.contradictions.append(
                    f"Large amount discrepancy: ₹{sorted_amounts[0]:,.2f} to ₹{sorted_amounts[-1]:,.2f}"
                )
                consistency_issues += 1

        result.consistency_score = round(max(0.0, 1.0 - consistency_issues / 3), 2)
        result.overall_score = round((result.completeness_score * 0.5) + (result.consistency_score * 0.5), 2)

        if result.completeness_score < 0.6:
            result.suggestions.append("Upload at least: purchase receipt, order ID, and complaint communication logs")
        if result.consistency_score < 0.8:
            result.suggestions.append("Review timeline for chronological accuracy and check amount references")
        if len(complaint.evidence) == 0:
            result.suggestions.append("No evidence provided at all; notice will be significantly weakened")
        if len(complaint.timeline) < 3:
            result.suggestions.append("Add more dated timeline entries to strengthen causation narrative")
        return result


def _extract_dates(timeline: list[str]) -> list[int]:
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    dates: list[int] = []
    for entry in timeline:
        match = _DATE_RE.search(entry)
        if match:
            day, month_str, year = match.groups()
            month = month_map.get(month_str[:3].lower(), 1)
            dates.append(int(year) * 10000 + month * 100 + int(day))
    return dates


def _extract_amounts(text: str) -> list[float]:
    amounts: list[float] = []
    for match in _AMOUNT_RE.finditer(text):
        try:
            amounts.append(float(match.group(1).replace(",", "")))
        except ValueError:
            continue
    return amounts
