"""Element-by-element civil claim analysis.

Uses Claude to evaluate whether the complaint narrative satisfies
the required civil claim elements for each plausible statutory section.
Falls back to keyword-based heuristics if LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from legaltech.legal_india import LawSection

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert Indian consumer law analyst. Given statutory sections and a complaint \
corpus, evaluate whether the complaint facts satisfy the required civil claim elements.

For EACH section, analyse these elements:
1. DUTY — Did the respondent owe a duty/obligation to the consumer?
2. BREACH — Did the respondent breach that duty (deficiency, unfair practice, non-compliance)?
3. CAUSATION — Did the breach directly cause the consumer's loss?
4. LOSS — Is there a quantifiable or demonstrable loss/harm?
5. MITIGATION — Did the consumer attempt to resolve before escalation?

Be rigorous but fair. Look for implicit signals:
- A consumer who contacted customer support has attempted mitigation even if not stated explicitly.
- A consumer who paid money and did not receive goods has demonstrable loss.
- Purchasing a product/service establishes duty.
- Timelines showing repeated follow-ups strengthen causation and mitigation.

Return JSON:
{
  "sections": [
    {
      "act": "exact act name",
      "section": "exact section ref",
      "elements": [
        {
          "element": "duty|breach|causation|loss|mitigation",
          "satisfied": true or false,
          "reasoning": "2-3 sentence explanation citing specific facts from the complaint"
        }
      ],
      "overall_pass": true or false,
      "score": 0.0 to 1.0
    }
  ]
}

Return ONLY the JSON array, no preamble.
"""


@dataclass
class ElementCheck:
    element: str
    satisfied: bool
    reasoning: str


@dataclass
class ClaimElementsResult:
    section: LawSection
    checks: list[ElementCheck] = field(default_factory=list)
    overall_pass: bool = False
    score: float = 0.0


# ── Fallback keyword signals (used when LLM unavailable) ──────────────

_ELEMENT_SIGNALS: dict[str, tuple[str, ...]] = {
    "duty": ("service", "product", "customer", "consumer", "subscription", "order"),
    "breach": ("failed", "refused", "not delivered", "defective", "delay", "ignored", "deficiency", "unfair", "misleading"),
    "causation": ("because", "due to", "result", "caused", "led to", "therefore", "consequently"),
    "loss": ("loss", "damage", "refund", "money", "amount", "cost", "expense", "compensation", "harm"),
    "mitigation": ("complained", "raised", "ticket", "support", "email", "called", "contacted", "escalated", "tried"),
}


class ClaimElementsAgent:
    """Evaluates whether complaint facts satisfy required civil claim elements."""

    def __init__(self, llm=None) -> None:
        self.llm = llm

    async def run(
        self,
        plausible_sections: list[LawSection],
        corpus: str,
    ) -> list[ClaimElementsResult]:
        if self.llm:
            try:
                return await self._agentic_run(plausible_sections, corpus)
            except Exception as exc:
                logger.warning("LLM claim elements failed, using fallback: %s", exc)
        return self._deterministic_run(plausible_sections, corpus)

    async def _agentic_run(
        self,
        plausible_sections: list[LawSection],
        corpus: str,
    ) -> list[ClaimElementsResult]:
        sections_info = "\n".join(
            f"- {s.act}, {s.section}: {s.title} — {s.why_relevant}"
            for s in plausible_sections
        )
        user_prompt = (
            f"## Applicable Sections\n{sections_info}\n\n"
            f"## Complaint Corpus\n{corpus[:4000]}"
        )
        data = await self.llm.complete_json(_SYSTEM_PROMPT, user_prompt)

        section_map = {(s.act, s.section): s for s in plausible_sections}
        results: list[ClaimElementsResult] = []

        for item in data.get("sections", []):
            key = (item.get("act", ""), item.get("section", ""))
            section = section_map.get(key)
            if not section:
                continue
            checks = [
                ElementCheck(
                    element=e["element"],
                    satisfied=bool(e["satisfied"]),
                    reasoning=e.get("reasoning", ""),
                )
                for e in item.get("elements", [])
            ]
            results.append(ClaimElementsResult(
                section=section,
                checks=checks,
                overall_pass=bool(item.get("overall_pass", False)),
                score=round(float(item.get("score", 0.0)), 2),
            ))

        covered = {(r.section.act, r.section.section) for r in results}
        for s in plausible_sections:
            if (s.act, s.section) not in covered:
                results.append(ClaimElementsResult(section=s, overall_pass=True, score=1.0))

        return results

    def _deterministic_run(
        self,
        plausible_sections: list[LawSection],
        corpus: str,
    ) -> list[ClaimElementsResult]:
        corpus_lower = corpus.lower()
        results: list[ClaimElementsResult] = []
        default_elements = ["duty", "breach", "causation", "loss", "mitigation"]

        for section in plausible_sections:
            checks: list[ElementCheck] = []
            for element in default_elements:
                signals = _ELEMENT_SIGNALS.get(element, ())
                found = [s for s in signals if s in corpus_lower]
                satisfied = len(found) > 0
                reasoning = (
                    f"Signals found: {', '.join(found)}" if satisfied
                    else f"No keywords matched for '{element}'; consider adding supporting facts"
                )
                checks.append(ElementCheck(element=element, satisfied=satisfied, reasoning=reasoning))

            passed = sum(1 for c in checks if c.satisfied)
            total = len(checks)
            score = passed / total if total > 0 else 0.0

            results.append(ClaimElementsResult(
                section=section,
                checks=checks,
                overall_pass=score >= 0.6,
                score=round(score, 2),
            ))

        return results
