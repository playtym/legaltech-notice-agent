"""Jurisdiction and forum determination for Indian consumer disputes.

Uses Claude to estimate claim value and determine appropriate consumer
commission. Falls back to regex-based amount extraction if LLM unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_AMOUNT_RE = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)", re.I)

_SYSTEM_PROMPT = """\
You are an Indian consumer law jurisdiction expert. Given a consumer complaint, \
determine the appropriate consumer commission and jurisdiction.

CPA 2019 PECUNIARY JURISDICTION:
- District Commission: claim ≤ ₹1 crore (CPA 2019 §34(1))
- State Commission: claim > ₹1 crore and ≤ ₹10 crore (CPA 2019 §47(1)(a)(i))
- National Commission: claim > ₹10 crore (CPA 2019 §58(1)(a)(i))

Estimate the claim value by considering:
- Direct monetary loss (refund amount, purchase price)
- Compensation for mental agony and harassment
- Litigation costs
- Any amounts mentioned in the complaint

TERRITORIAL JURISDICTION:
- Where the opposite party resides or carries on business
- Where the cause of action arose (CPA 2019 §34(2)/§35)

Return JSON:
{
  "estimated_claim_value": float or null,
  "forum": "District Commission|State Commission|National Commission",
  "pecuniary_basis": "explanation of pecuniary jurisdiction",
  "territorial_basis": "explanation of territorial jurisdiction",
  "filing_notes": ["list of important filing notes"],
  "section_reference": "CPA 2019 section references"
}

Return ONLY the JSON.
"""


@dataclass
class JurisdictionResult:
    forum: str
    pecuniary_basis: str
    territorial_basis: str
    complainant_location: str
    estimated_claim_value: float | None
    section_reference: str
    filing_notes: list[str]


# CPA 2019 pecuniary jurisdiction thresholds
_DISTRICT_LIMIT = 1_00_00_000      # ₹1 crore
_STATE_LIMIT = 10_00_00_000        # ₹10 crore


def _estimate_claim_value(corpus: str) -> float | None:
    amounts: list[float] = []
    for match in _AMOUNT_RE.finditer(corpus):
        try:
            amounts.append(float(match.group(1).replace(",", "")))
        except ValueError:
            continue
    return max(amounts) if amounts else None


def determine_jurisdiction(
    complainant_address: str | None,
    issue_summary: str,
    desired_resolution: str,
    timeline: list[str],
    evidence: list[str],
) -> JurisdictionResult:
    """Deterministic fallback."""
    corpus = " ".join([issue_summary, desired_resolution, *timeline, *evidence])
    claim_value = _estimate_claim_value(corpus)
    location = complainant_address or "[complainant location not provided]"

    if claim_value is None:
        forum = "District Commission (default — claim value not quantified)"
        pecuniary = "Claim value could not be estimated; defaults to District Commission"
    elif claim_value <= _DISTRICT_LIMIT:
        forum = "District Consumer Disputes Redressal Commission"
        pecuniary = f"Estimated claim ₹{claim_value:,.0f} ≤ ₹1 crore (CPA 2019 §34(1))"
    elif claim_value <= _STATE_LIMIT:
        forum = "State Consumer Disputes Redressal Commission"
        pecuniary = f"Estimated claim ₹{claim_value:,.0f} > ₹1 crore and ≤ ₹10 crore (CPA 2019 §47(1)(a)(i))"
    else:
        forum = "National Consumer Disputes Redressal Commission"
        pecuniary = f"Estimated claim ₹{claim_value:,.0f} > ₹10 crore (CPA 2019 §58(1)(a)(i))"

    territorial = (
        f"Territorial jurisdiction: where the opposite party resides or carries on business, "
        f"or where the cause of action arose (CPA 2019 §34(2)/§35). Complainant location: {location}"
    )
    filing_notes = [
        "File complaint in writing or electronically via e-daakhil.nic.in",
        "Attach copies of all evidence listed in the notice",
        "Pay prescribed filing fee per Consumer Protection (Consumer Commission Procedure) Regulations, 2020",
        "Limitation: complaint must be filed within 2 years from date cause of action arose (CPA 2019 §69(1))",
    ]
    if claim_value and claim_value > 5_00_000:
        filing_notes.append("For claims above ₹5 lakhs, consider engaging an advocate")

    return JurisdictionResult(
        forum=forum, pecuniary_basis=pecuniary, territorial_basis=territorial,
        complainant_location=location, estimated_claim_value=claim_value,
        section_reference="CPA 2019 §§34, 47, 58 (pecuniary); §35 (territorial)",
        filing_notes=filing_notes,
    )


class JurisdictionAgent:
    """LLM-powered jurisdiction determination with deterministic fallback."""

    def __init__(self, llm=None) -> None:
        self.llm = llm

    async def run(
        self,
        complainant_address: str | None,
        issue_summary: str,
        desired_resolution: str,
        timeline: list[str],
        evidence: list[str],
    ) -> JurisdictionResult:
        if self.llm:
            try:
                return await self._agentic_run(
                    complainant_address, issue_summary, desired_resolution, timeline, evidence,
                )
            except Exception as exc:
                logger.warning("LLM jurisdiction analysis failed, using fallback: %s", exc)
        return determine_jurisdiction(complainant_address, issue_summary, desired_resolution, timeline, evidence)

    async def _agentic_run(
        self,
        complainant_address: str | None,
        issue_summary: str,
        desired_resolution: str,
        timeline: list[str],
        evidence: list[str],
    ) -> JurisdictionResult:
        location = complainant_address or "[not provided]"
        user_prompt = (
            f"## Issue Summary\n{issue_summary}\n\n"
            f"## Desired Resolution\n{desired_resolution}\n\n"
            f"## Complainant Location\n{location}\n\n"
            f"## Timeline\n" + "\n".join(f"- {t}" for t in timeline) + "\n\n"
            f"## Evidence\n" + "\n".join(f"- {e}" for e in evidence)
        )
        data = await self.llm.complete_json(_SYSTEM_PROMPT, user_prompt)
        claim_value = data.get("estimated_claim_value")
        if claim_value is not None:
            claim_value = float(claim_value)
        return JurisdictionResult(
            forum=data.get("forum", "District Commission"),
            pecuniary_basis=data.get("pecuniary_basis", ""),
            territorial_basis=data.get("territorial_basis", f"Complainant location: {location}"),
            complainant_location=location,
            estimated_claim_value=claim_value,
            section_reference=data.get("section_reference", "CPA 2019 §§34, 47, 58"),
            filing_notes=data.get("filing_notes", []),
        )
