"""Jurisdiction and forum determination for Indian consumer disputes.

Determines the appropriate consumer commission (District/State/National)
based on claim value and territorial jurisdiction per CPA 2019.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_AMOUNT_RE = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)", re.I)


@dataclass
class JurisdictionResult:
    forum: str                    # "District Commission" / "State Commission" / "National Commission"
    pecuniary_basis: str          # e.g. "Claim value ≤ ₹1 crore"
    territorial_basis: str        # e.g. "Where cause of action arose"
    complainant_location: str
    estimated_claim_value: float | None
    section_reference: str
    filing_notes: list[str]


# CPA 2019 pecuniary jurisdiction thresholds (after 2024 amendment notification)
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
    corpus = " ".join([issue_summary, desired_resolution, *timeline, *evidence])
    claim_value = _estimate_claim_value(corpus)
    location = complainant_address or "[complainant location not provided]"

    # Determine forum by pecuniary jurisdiction
    if claim_value is None:
        forum = "District Commission (default — claim value not quantified)"
        pecuniary = "Claim value could not be automatically estimated; defaults to District Commission"
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
        f"or where the cause of action arose (CPA 2019 §34(2)/§35). "
        f"Complainant location: {location}"
    )

    filing_notes = [
        "File complaint in writing or electronically via e-daakhil.nic.in",
        "Attach copies of all evidence listed in the notice",
        "Pay prescribed filing fee per Consumer Protection (Consumer Commission Procedure) Regulations, 2020",
        "Limitation: complaint must be filed within 2 years from date cause of action arose (CPA 2019 §69(1))",
    ]

    if claim_value and claim_value > 5_00_000:
        filing_notes.append(
            "For claims above ₹5 lakhs, consider engaging an advocate for commission proceedings"
        )

    return JurisdictionResult(
        forum=forum,
        pecuniary_basis=pecuniary,
        territorial_basis=territorial,
        complainant_location=location,
        estimated_claim_value=claim_value,
        section_reference="CPA 2019 §§34, 47, 58 (pecuniary); §35 (territorial)",
        filing_notes=filing_notes,
    )
