"""Dynamic cure period determination.

Assigns a reasonable cure period based on the type and complexity of
the dispute, instead of a static 15-day blanket that can be challenged
as unreasonable or coercive.
"""

from __future__ import annotations


def determine_cure_period(issue_summary: str, timeline_length: int) -> tuple[int, str]:
    """Returns (days, explanation) for the cure period."""
    lower = issue_summary.lower()

    # Urgent: unauthorized financial transactions → 7 days
    if any(k in lower for k in ("unauthorized transaction", "fraud", "hacked", "stolen")):
        return 7, "7 days (urgent — unauthorized financial transaction per RBI circular on zero-liability timeline)"

    # Payment reversals / simple refunds → 15 days
    if any(k in lower for k in ("refund", "payment failed", "double charged", "overcharged")):
        return 15, "15 days (standard refund/payment reversal per RBI and e-commerce norms)"

    # Service deficiency / delivery issues → 15 days
    if any(k in lower for k in ("not delivered", "delivery", "delay", "deficiency")):
        return 15, "15 days (standard service resolution period)"

    # Product defect / replacement → 21 days
    if any(k in lower for k in ("defective", "damaged", "faulty", "replacement", "repair")):
        return 21, "21 days (reasonable period for product inspection and replacement logistics)"

    # Data breach / privacy → 30 days
    if any(k in lower for k in ("data leak", "privacy", "personal data", "security breach")):
        return 30, "30 days (per IT Act reasonable security practices timeline and DPDP Act notification period)"

    # Complex disputes with long timelines → 30 days
    if timeline_length >= 5:
        return 30, "30 days (complex dispute with extended history requiring internal review)"

    # Default
    return 15, "15 days (standard consumer grievance resolution period)"
