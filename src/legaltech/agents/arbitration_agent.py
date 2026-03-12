"""Arbitration clause detection agent.

Uses Claude to analyse extracted policy text for arbitration, mediation,
and ADR clauses, and determine legal impact. Falls back to regex-based
detection if LLM unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from legaltech.schemas import PolicyEvidence

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert Indian dispute resolution lawyer. Analyse the company's policy/T&C \
text for arbitration, mediation, ADR, and jurisdiction restriction clauses.

For each clause found, determine:
1. The clause type (arbitration, mediation, jurisdiction_restriction, class_action_waiver)
2. The exact text excerpt
3. Legal impact on the consumer's case
4. Whether it can be overridden under Indian consumer law

KEY LEGAL PRINCIPLES:
- CPA 2019 §2(7)(ii): consumer forums are NOT bound by arbitration agreements
- Emaar MGF v. Aftab Singh (2019) 12 SCC 1: arbitration clause no bar to consumer forum
- CPA 2019 §35: consumer can file where complaint arose regardless of contractual forum clause
- CPA 2019 §35(1)(c): consumer associations can file regardless of class action waivers

Return JSON:
{
  "has_arbitration_clause": true/false,
  "has_jurisdiction_restriction": true/false,
  "has_class_action_waiver": true/false,
  "restricted_jurisdiction": "city name" or null,
  "clauses": [
    {
      "text_excerpt": "quoted clause text",
      "source_url": "URL",
      "clause_type": "arbitration|mediation|jurisdiction_restriction|class_action_waiver"
    }
  ],
  "legal_impact": "comprehensive analysis of how these clauses affect the consumer",
  "recommendation": "specific advice for the consumer, citing statutory overrides"
}

Return ONLY the JSON.
"""


_ARBITRATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"arbitrat(?:ion|or|e)", re.I),
    re.compile(r"binding\s+(?:arbitration|dispute\s+resolution)", re.I),
    re.compile(r"(?:disputes?|claims?)\s+shall\s+be\s+(?:resolved|settled|referred)\s+(?:through|by|to)\s+(?:arbitration|mediation|adr)", re.I),
    re.compile(r"(?:indian|international)\s+(?:arbitration|chamber)", re.I),
    re.compile(r"Section\s+(?:7|8|11)\s+(?:of\s+)?(?:the\s+)?Arbitration", re.I),
    re.compile(r"(?:SIAC|ICC|LCIA|ICA|MCIA)\s+(?:rules|arbitration)", re.I),
    re.compile(r"(?:mediat(?:ion|or)|conciliat(?:ion|or))", re.I),
    re.compile(r"(?:waive|waiver)\s+(?:of\s+)?(?:right\s+to\s+)?(?:sue|class\s+action|court)", re.I),
]

_JURISDICTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:exclusive\s+)?jurisdiction\s+(?:of\s+)?(?:courts?\s+(?:at|in|of)\s+)(\w[\w\s,]+)", re.I),
    re.compile(r"subject\s+to\s+(?:the\s+)?(?:exclusive\s+)?jurisdiction\s+of\s+(\w[\w\s,]+?)(?:courts?|tribunals?)", re.I),
]


@dataclass
class ArbitrationClause:
    text_excerpt: str
    source_url: str
    clause_type: str  # "arbitration", "mediation", "jurisdiction_restriction", "class_action_waiver"


@dataclass
class ArbitrationCheckResult:
    has_arbitration_clause: bool = False
    has_jurisdiction_restriction: bool = False
    has_class_action_waiver: bool = False
    restricted_jurisdiction: str | None = None
    clauses_found: list[ArbitrationClause] = field(default_factory=list)
    legal_impact: str = ""
    recommendation: str = ""


class ArbitrationDetectionAgent:
    """Scans policy evidence for arbitration/ADR clauses that affect notice strategy."""

    def __init__(self, llm=None) -> None:
        self.llm = llm

    async def run(self, policy_evidence: list[PolicyEvidence]) -> ArbitrationCheckResult:
        if self.llm:
            try:
                return await self._agentic_run(policy_evidence)
            except Exception as exc:
                logger.warning("LLM arbitration analysis failed, using fallback: %s", exc)
        return self._deterministic_run(policy_evidence)

    async def _agentic_run(self, policy_evidence: list[PolicyEvidence]) -> ArbitrationCheckResult:
        policy_text = "\n\n".join(
            f"[Source: {p.source_url}]\n{p.excerpt[:1000]}"
            for p in policy_evidence
        ) if policy_evidence else "(No policy text available)"

        data = await self.llm.complete_json(
            _SYSTEM_PROMPT,
            f"## Company Policy/T&C Text\n{policy_text}",
        )

        clauses = [
            ArbitrationClause(
                text_excerpt=c.get("text_excerpt", ""),
                source_url=c.get("source_url", "llm-analysis"),
                clause_type=c.get("clause_type", "arbitration"),
            )
            for c in data.get("clauses", [])
        ]

        return ArbitrationCheckResult(
            has_arbitration_clause=bool(data.get("has_arbitration_clause", False)),
            has_jurisdiction_restriction=bool(data.get("has_jurisdiction_restriction", False)),
            has_class_action_waiver=bool(data.get("has_class_action_waiver", False)),
            restricted_jurisdiction=data.get("restricted_jurisdiction"),
            clauses_found=clauses,
            legal_impact=data.get("legal_impact", ""),
            recommendation=data.get("recommendation", ""),
        )

    def _deterministic_run(self, policy_evidence: list[PolicyEvidence]) -> ArbitrationCheckResult:
        result = ArbitrationCheckResult()

        for policy in policy_evidence:
            text = policy.excerpt
            lower = text.lower()

            # Check arbitration patterns
            for pattern in _ARBITRATION_PATTERNS:
                match = pattern.search(text)
                if match:
                    start = max(0, match.start() - 80)
                    end = min(len(text), match.end() + 120)
                    excerpt = text[start:end].strip()

                    if "waiv" in lower and ("class action" in lower or "court" in lower or "sue" in lower):
                        clause_type = "class_action_waiver"
                        result.has_class_action_waiver = True
                    elif "mediat" in match.group(0).lower() or "conciliat" in match.group(0).lower():
                        clause_type = "mediation"
                    else:
                        clause_type = "arbitration"
                        result.has_arbitration_clause = True

                    result.clauses_found.append(ArbitrationClause(
                        text_excerpt=excerpt,
                        source_url=policy.source_url,
                        clause_type=clause_type,
                    ))

            # Check jurisdiction restriction patterns
            for jp in _JURISDICTION_PATTERNS:
                jm = jp.search(text)
                if jm:
                    result.has_jurisdiction_restriction = True
                    result.restricted_jurisdiction = jm.group(1).strip().rstrip(".,;")
                    result.clauses_found.append(ArbitrationClause(
                        text_excerpt=jm.group(0)[:200],
                        source_url=policy.source_url,
                        clause_type="jurisdiction_restriction",
                    ))

        # Build legal impact and recommendation
        impacts = []
        recommendations = []

        if result.has_arbitration_clause:
            impacts.append(
                "Company's terms contain an arbitration clause. Under Section 8, Arbitration & Conciliation Act, 1996, "
                "the company may seek to refer this dispute to arbitration and move to stay consumer proceedings."
            )
            recommendations.append(
                "NOTE: CPA 2019 Section 2(7)(ii) clarifies that consumer forums are NOT bound by arbitration agreements "
                "in consumer disputes. You can still file before Consumer Commission. However, mention awareness of the "
                "arbitration clause in your notice and assert your statutory consumer right to approach the Commission."
            )

        if result.has_jurisdiction_restriction:
            impacts.append(
                f"Terms restrict jurisdiction to courts in '{result.restricted_jurisdiction}'. "
                "This may limit where you can escalate."
            )
            recommendations.append(
                "Under CPA 2019 Section 35, consumer can file where the complaint arose OR where the opposite party "
                "resides/carries on business. Contractual jurisdiction clauses are generally overridden by CPA for consumer disputes."
            )

        if result.has_class_action_waiver:
            impacts.append(
                "Terms include a class action waiver. This may limit collective consumer action."
            )
            recommendations.append(
                "Class action waivers have limited enforceability in Indian consumer law. "
                "CPA 2019 Section 35(1)(c) allows complaints by consumer associations regardless of T&C waivers."
            )

        if not result.clauses_found:
            impacts.append("No arbitration, mediation, or jurisdiction restriction clauses detected in scraped policy text.")
            recommendations.append("Proceed with standard consumer notice. Re-check full T&Cs manually for completeness.")

        result.legal_impact = " | ".join(impacts)
        result.recommendation = " | ".join(recommendations)
        return result
