import json
import logging
from dataclasses import dataclass
import re

from legaltech.schemas import ComplaintInput

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a legal intake analyst for Indian consumer complaints. Given a raw complaint \
text (which may be in English, Hindi, Hinglish, or a mix), your job is to:

1. Normalize the text into clear, factual English suitable for a legal notice
2. Fix grammar and spelling while preserving all factual details
3. Translate any Hindi/Hinglish phrases to English
4. Identify missing critical facts
5. Flag any quality issues (vague language, extreme claims, etc.)

Return JSON:
{
  "normalized_issue": "clean English version of the complaint",
  "missing_facts": ["list of missing critical facts"],
  "smell_test_flags": ["list of quality concerns"]
}

Do NOT invent or add facts. Only normalize what is provided.
Return ONLY the JSON.
"""


@dataclass
class IntakeAnalysis:
    normalized_issue: str
    missing_facts: list[str]
    smell_test_flags: list[str]


class IntakeAgent:
    """Normalizes typed/transcribed complaint and performs quality checks."""

    def __init__(self, llm=None) -> None:
        self.llm = llm

    async def run(self, complaint: ComplaintInput) -> IntakeAnalysis:
        if self.llm:
            try:
                return await self._agentic_run(complaint)
            except Exception as exc:
                logger.warning("LLM intake normalization failed, using fallback: %s", exc)
        return self._deterministic_run(complaint)

    async def _agentic_run(self, complaint: ComplaintInput) -> IntakeAnalysis:
        source_text = complaint.transcript_text or complaint.issue_summary
        user_prompt = (
            f"## Raw Complaint Text\n{source_text}\n\n"
            f"## Company: {complaint.company_name_hint or 'not specified'}\n"
            f"## Website: {complaint.website or 'not provided'}\n"
            f"## Timeline entries: {len(complaint.timeline)}\n"
            f"## Evidence items: {len(complaint.evidence)}\n"
            f"## Input mode: {complaint.mode.value}"
        )
        data = await self.llm.complete_json(_SYSTEM_PROMPT, user_prompt)
        return IntakeAnalysis(
            normalized_issue=data.get("normalized_issue", source_text),
            missing_facts=data.get("missing_facts", []),
            smell_test_flags=data.get("smell_test_flags", []),
        )

    def _deterministic_run(self, complaint: ComplaintInput) -> IntakeAnalysis:
        source_text = complaint.transcript_text or complaint.issue_summary
        normalized = self._normalize_hinglish(source_text)

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

    @staticmethod
    def _normalize_hinglish(text: str) -> str:
        normalized = " ".join(text.split())
        replacements = {
            "mera": "my", "meri": "my", "mere": "my",
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
