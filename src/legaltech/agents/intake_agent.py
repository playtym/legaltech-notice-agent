from dataclasses import dataclass
import re

from legaltech.schemas import ComplaintInput


@dataclass
class IntakeAnalysis:
    normalized_issue: str
    missing_facts: list[str]
    smell_test_flags: list[str]


class IntakeAgent:
    """Normalizes typed/transcribed complaint and performs basic quality checks."""

    def _normalize_hinglish_to_english(self, text: str) -> str:
        normalized = " ".join(text.split())

        # Lightweight normalization for common Hinglish intake patterns.
        replacements = {
            "mera": "my",
            "meri": "my",
            "mere": "my",
            "order nahi aaya": "order not delivered",
            "refund nahi mila": "refund not received",
            "paise kat gaye": "amount was debited",
            "koi response nahi": "no response",
            "support reply nahi kar raha": "support is not responding",
            "galat product": "wrong product",
            "defective aaya": "received defective item",
        }
        lower = normalized.lower()
        for src, dst in replacements.items():
            lower = lower.replace(src, dst)

        lower = re.sub(r"\s+", " ", lower).strip()
        if lower:
            return lower[0].upper() + lower[1:]
        return normalized

    async def run(self, complaint: ComplaintInput) -> IntakeAnalysis:
        source_text = complaint.transcript_text or complaint.issue_summary
        normalized = self._normalize_hinglish_to_english(source_text)

        missing: list[str] = []
        if len(complaint.timeline) == 0:
            missing.append("Timeline of events with dates is missing")
        if len(complaint.evidence) == 0:
            missing.append(
                "Upload supporting documents: purchase receipt/invoice, order number, payment proof, and complaint emails/chats/screenshots"
            )
        if complaint.website is None and complaint.company_name_hint is None:
            missing.append("Company identity signal missing (website or company name)")

        smell_flags: list[str] = []
        if len(normalized) < 60:
            smell_flags.append("Narrative too short for a legally robust notice")

        extreme_words = ("always", "never", "100%", "all fraud")
        if any(w in normalized.lower() for w in extreme_words):
            smell_flags.append("Overbroad language detected; consider fact-specific wording")

        if complaint.mode.value == "voice":
            smell_flags.append("Voice transcript normalized from mixed Hindi-English to English for legal drafting")

        return IntakeAnalysis(
            normalized_issue=normalized,
            missing_facts=missing,
            smell_test_flags=smell_flags,
        )
