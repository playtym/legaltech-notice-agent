"""Evidence consistency scoring and contradiction detection.

Analyses the evidence list, timeline, and issue summary for internal
consistency, completeness, and potential contradictions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from legaltech.schemas import ComplaintInput


@dataclass
class EvidenceScore:
    overall_score: float = 0.0        # 0.0–1.0
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    contradictions: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


# Date pattern to extract from timeline entries
_DATE_RE = re.compile(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})\b", re.I)
_AMOUNT_RE = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)", re.I)


class EvidenceScoringAgent:
    """Scores evidence quality, detects contradictions, and suggests improvements."""

    async def run(self, complaint: ComplaintInput, normalized_issue: str) -> EvidenceScore:
        result = EvidenceScore()

        # ── 1. Completeness scoring ──────────────────────────────────
        expected_evidence_types = {
            "receipt_or_invoice": ("invoice", "receipt", "bill", "order"),
            "order_id": ("order number", "order id", "order #", "reference"),
            "payment_proof": ("payment", "transaction", "upi", "bank", "card", "wallet"),
            "communication": ("email", "chat", "ticket", "call", "sms", "whatsapp"),
            "screenshot": ("screenshot", "photo", "image", "attachment"),
        }

        corpus = " ".join([
            normalized_issue,
            " ".join(complaint.evidence),
            " ".join(complaint.timeline),
        ]).lower()

        found_types = 0
        for etype, keywords in expected_evidence_types.items():
            if any(k in corpus for k in keywords):
                found_types += 1
            else:
                result.gaps.append(f"Missing evidence type: {etype.replace('_', ' ')}")

        result.completeness_score = round(found_types / len(expected_evidence_types), 2)

        # ── 2. Timeline consistency ──────────────────────────────────
        timeline_dates = _extract_dates(complaint.timeline)
        consistency_issues = 0

        if len(timeline_dates) >= 2:
            for i in range(1, len(timeline_dates)):
                if timeline_dates[i] < timeline_dates[i - 1]:
                    result.contradictions.append(
                        f"Timeline order issue: entry {i + 1} date appears before entry {i} date"
                    )
                    consistency_issues += 1

        # ── 3. Amount consistency ────────────────────────────────────
        amounts_in_issue = _extract_amounts(normalized_issue)
        amounts_in_evidence = _extract_amounts(" ".join(complaint.evidence))
        all_amounts = set(amounts_in_issue + amounts_in_evidence)

        if len(all_amounts) > 1:
            sorted_amounts = sorted(all_amounts)
            if sorted_amounts[-1] > sorted_amounts[0] * 10:
                result.contradictions.append(
                    f"Large amount discrepancy detected: values range from ₹{sorted_amounts[0]:,.2f} to ₹{sorted_amounts[-1]:,.2f}"
                )
                consistency_issues += 1

        # ── 4. Cross-reference issue text vs evidence ────────────────
        issue_lower = normalized_issue.lower()
        if "refund" in issue_lower and not any("refund" in e.lower() for e in complaint.evidence):
            result.gaps.append("Issue mentions refund but no refund-related evidence listed (e.g. refund request screenshot, bank statement)")

        if "delivered" in issue_lower or "delivery" in issue_lower:
            if not any(k in " ".join(complaint.evidence).lower() for k in ("delivery", "tracking", "shipping", "courier")):
                result.gaps.append("Issue mentions delivery but no delivery/tracking evidence listed")

        if "support" in issue_lower or "complaint" in issue_lower:
            if not any(k in " ".join(complaint.evidence).lower() for k in ("ticket", "chat", "email", "call")):
                result.gaps.append("Issue mentions support interaction but no communication records listed")

        # ── 5. Score computation ─────────────────────────────────────
        max_consistency_issues = 3
        consistency_deduction = min(consistency_issues / max_consistency_issues, 1.0)
        result.consistency_score = round(1.0 - consistency_deduction, 2)

        result.overall_score = round(
            (result.completeness_score * 0.5) + (result.consistency_score * 0.5), 2
        )

        # ── 6. Suggestions ───────────────────────────────────────────
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
    """Extract approximate ordinal dates (as YYYYMMDD ints) from timeline strings."""
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
            ordinal = int(year) * 10000 + month * 100 + int(day)
            dates.append(ordinal)
    return dates


def _extract_amounts(text: str) -> list[float]:
    """Extract INR amounts from text."""
    amounts: list[float] = []
    for match in _AMOUNT_RE.finditer(text):
        try:
            amounts.append(float(match.group(1).replace(",", "")))
        except ValueError:
            continue
    return amounts
