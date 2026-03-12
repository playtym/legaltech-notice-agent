from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from legaltech.legal_india import LawSection, match_law_sections
from legaltech.schemas import ComplaintInput, PolicyEvidence
from legaltech.services.legal_db import BareActEntry, lookup_all_matched

logger = logging.getLogger(__name__)

_LEGAL_RESEARCH_SYSTEM_PROMPT = """\
You are an expert Indian consumer/civil law researcher. Given a complaint summary, \
identify ALL applicable Indian statutory provisions that could support the complainant's case.

You MUST return a JSON array of objects. Each object has these exact keys:
- "act": Full name of the Indian statute (e.g. "Information Technology Act, 2000")
- "section": Section reference (e.g. "Section 79" or "Section 79 read with IT Rules 2021, Rule 3")
- "title": Short title of the provision
- "why_relevant": 2-3 sentence explanation of why this section applies to these specific facts
- "legacy_reference": If the section replaces an older provision, note it here (else null)

SCOPE: Indian statutes and rules only. Civil/consumer remedies only — no criminal sections \
unless they have civil consequence provisions (e.g. IT Act §43A civil compensation). \
Include constitutional provisions (Article 14, 19, 21) ONLY where directly actionable \
(e.g. writ jurisdiction against state actors or intermediary obligations under Article 19(1)(a)).

Include sui generis provisions (intermediary guidelines, sector-specific rules, TRAI/RBI/SEBI \
regulations, IRDAI regulations, RERA, etc.) where applicable.

Be comprehensive — identify 5-15 provisions. Better to over-include than miss applicable law.

Return ONLY the JSON array, no preamble or explanation.
"""


@dataclass
class LegalAnalysis:
    plausible_sections: list[LawSection]
    bare_act_entries: list[BareActEntry] = field(default_factory=list)
    spirit_of_law_view: str = ""
    reasonableness_view: str = ""
    risk_flags: list[str] = field(default_factory=list)
    used_llm_research: bool = False


class LegalAnalysisAgent:
    """Indian-jurisdiction legal plausibility analysis.

    Uses a rule-based engine for known patterns plus Claude as a fallback
    legal researcher for out-of-syllabus cases the rule engine doesn't cover.

    This does not replace a licensed advocate's advice.
    """

    def __init__(self, llm=None) -> None:
        self.llm = llm  # LLMService — optional, enables Claude fallback

    @staticmethod
    def _needs_llm_boost(corpus: str, plausible_count: int, policy_count: int) -> bool:
        """Decide whether rule-based legal matching likely needs LLM augmentation."""
        if plausible_count <= 2:
            return True

        complex_markers = (
            "upi",
            "wallet",
            "payment gateway",
            "subscription",
            "chargeback",
            "auto debit",
            "dark pattern",
            "privacy",
            "data breach",
            "intermediary",
            "platform",
            "marketplace",
            "fintech",
            "insurance",
            "sebi",
            "rbi",
            "irda",
            "telecom",
            "ai",
            "algorithm",
        )
        low_coverage_complex_case = plausible_count <= 4 and any(m in corpus.lower() for m in complex_markers)
        policy_dense_but_low_sections = policy_count >= 2 and plausible_count <= 3
        return low_coverage_complex_case or policy_dense_but_low_sections

    async def run(
        self,
        complaint: ComplaintInput,
        policy_evidence: list[PolicyEvidence],
        normalized_issue: str,
    ) -> LegalAnalysis:
        corpus = " ".join(
            [
                complaint.issue_summary,
                complaint.desired_resolution,
                normalized_issue,
                " ".join(complaint.timeline),
                " ".join(e.excerpt for e in policy_evidence),
            ]
        )

        # ── Phase 1: Rule-based matching against known sections ──────
        plausible = match_law_sections(corpus)
        bare_act_entries = lookup_all_matched([s.section for s in plausible])

        used_llm = False

        # ── Phase 2: Claude fallback for out-of-syllabus/complex cases ───────
        if self.llm and self._needs_llm_boost(corpus, len(plausible), len(policy_evidence)):
            llm_sections = await self._claude_legal_research(
                complaint=complaint,
                normalized_issue=normalized_issue,
                existing_sections=plausible,
            )
            if llm_sections:
                # Merge: keep rule-engine matches, add Claude-discovered ones
                existing_keys = {(s.act, s.section) for s in plausible}
                for ls in llm_sections:
                    if (ls.act, ls.section) not in existing_keys:
                        plausible.append(ls)
                        existing_keys.add((ls.act, ls.section))
                used_llm = True
                logger.info(
                    "Claude legal research added %d sections (rule engine had %d)",
                    len(llm_sections), len(plausible) - len(llm_sections),
                )

        risk_flags: list[str] = []

        if len(complaint.timeline) < 2:
            risk_flags.append("Sparse chronology may weaken causation and quantum claims")
        if len(complaint.evidence) == 0:
            risk_flags.append("No documentary evidence listed")
        if complaint.website is None:
            risk_flags.append("No official website supplied; respondent identification risk")

        criminal_indicators = ("fraud", "cheat", "criminal", "police complaint", "fir")
        if any(token in corpus.lower() for token in criminal_indicators):
            risk_flags.append(
                "Potential criminal allegations detected in intake text; excluded from section-citation because this workflow is civil-only"
            )

        spirit = (
            "The complaint appears to invoke consumer fairness principles: transparent terms, "
            "non-deficient service, and good-faith grievance handling."
        )

        reasonableness = (
            "A reasonable notice should stick to verifiable facts, proportional remedies "
            "(refund/replacement/compensation), and a fair cure period before escalation."
        )

        return LegalAnalysis(
            plausible_sections=plausible,
            bare_act_entries=bare_act_entries,
            spirit_of_law_view=spirit,
            reasonableness_view=reasonableness,
            risk_flags=risk_flags,
            used_llm_research=used_llm,
        )

    async def _claude_legal_research(
        self,
        complaint: ComplaintInput,
        normalized_issue: str,
        existing_sections: list[LawSection],
    ) -> list[LawSection]:
        """Ask Claude to identify applicable Indian law provisions."""
        existing_labels = ", ".join(f"{s.act} {s.section}" for s in existing_sections)
        user_prompt = (
            f"COMPLAINT SUMMARY:\n{complaint.issue_summary}\n\n"
            f"NORMALIZED ISSUE:\n{normalized_issue}\n\n"
            f"DESIRED RESOLUTION:\n{complaint.desired_resolution}\n\n"
            f"TIMELINE:\n" + "\n".join(complaint.timeline) + "\n\n"
            f"COMPANY: {complaint.company_name_hint or 'unknown'}\n"
            f"WEBSITE: {complaint.website or 'not provided'}\n\n"
        )
        if existing_labels:
            user_prompt += (
                f"ALREADY IDENTIFIED (do NOT repeat these, find ADDITIONAL provisions):\n"
                f"{existing_labels}\n"
            )

        try:
            data = await self.llm.complete_json(
                _LEGAL_RESEARCH_SYSTEM_PROMPT, user_prompt
            )
            sections: list[LawSection] = []
            items = data if isinstance(data, list) else data.get("provisions", data.get("sections", []))
            for item in items:
                sections.append(LawSection(
                    act=item["act"],
                    section=item["section"],
                    title=item.get("title", ""),
                    trigger_keywords=(),  # Claude-discovered, no keywords
                    why_relevant=item.get("why_relevant", ""),
                    legacy_reference=item.get("legacy_reference"),
                ))
            return sections
        except Exception as exc:
            logger.warning("Claude legal research failed (non-fatal): %s", exc)
            return []
