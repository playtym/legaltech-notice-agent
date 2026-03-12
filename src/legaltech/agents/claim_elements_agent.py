"""Element-by-element civil claim analysis.

For each plausible section, checks whether the complaint narrative
satisfies the required civil claim elements before allowing citation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from legaltech.legal_india import LawSection


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


# ── Civil claim elements per section family ──────────────────────────────

_CIVIL_ELEMENTS: dict[str, list[str]] = {
    "Consumer Protection Act, 2019": [
        "duty",          # respondent owed a duty to the consumer
        "breach",        # respondent breached that duty / deficiency / unfair practice
        "causation",     # breach caused the consumer's loss
        "loss",          # quantifiable or demonstrable loss/harm
        "mitigation",    # consumer attempted to resolve before escalation
    ],
    "Indian Contract Act, 1872": [
        "valid_contract",  # a valid contract existed between parties
        "breach",          # respondent breached a term of the contract
        "causation",       # breach led to actual loss
        "loss",            # loss that naturally arose or was foreseeable
        "mitigation",      # consumer mitigated / attempted resolution
    ],
    "Information Technology Act, 2000": [
        "data_handling",   # respondent handled sensitive personal data
        "negligence",      # failure to implement reasonable security practices
        "causation",       # negligence caused wrongful loss/gain
        "loss",            # demonstrable wrongful loss or gain
        "mitigation",      # consumer reported and sought resolution
    ],
    "Payment and Settlement Systems Act, 2007": [
        "regulated_entity",  # respondent is a regulated payment system participant
        "obligation",        # specific RBI direction / ombudsman norm applicable
        "breach",            # respondent failed to comply
        "loss",              # consumer suffered monetary loss / denial of service
        "mitigation",        # complaint raised with entity, 30-day rule for ombudsman
    ],
}

# ── Keyword signals for each element ─────────────────────────────────────

_ELEMENT_SIGNALS: dict[str, tuple[str, ...]] = {
    "duty": ("service", "product", "customer", "consumer", "subscription", "order"),
    "breach": ("failed", "refused", "not delivered", "defective", "delay", "ignored", "deficiency", "unfair", "misleading"),
    "causation": ("because", "due to", "result", "caused", "led to", "therefore", "consequently"),
    "loss": ("loss", "damage", "refund", "money", "amount", "cost", "expense", "compensation", "harm"),
    "mitigation": ("complained", "raised", "ticket", "support", "email", "called", "contacted", "escalated", "tried"),
    "valid_contract": ("order", "purchase", "agreement", "subscription", "paid", "contract", "invoice", "booked"),
    "data_handling": ("data", "personal information", "account", "profile", "sensitive", "password"),
    "negligence": ("leak", "exposed", "hack", "security", "negligent", "no protection", "breach"),
    "regulated_entity": ("bank", "wallet", "upi", "payment", "rbi", "nbfc", "fintech"),
    "obligation": ("rbi", "ombudsman", "regulation", "circular", "direction", "mandate"),
}


class ClaimElementsAgent:
    """Evaluates whether complaint facts satisfy required civil claim elements."""

    async def run(
        self,
        plausible_sections: list[LawSection],
        corpus: str,
    ) -> list[ClaimElementsResult]:
        corpus_lower = corpus.lower()
        results: list[ClaimElementsResult] = []

        for section in plausible_sections:
            elements = _CIVIL_ELEMENTS.get(section.act)
            if not elements:
                results.append(ClaimElementsResult(section=section, overall_pass=True, score=1.0))
                continue

            checks: list[ElementCheck] = []
            for element in elements:
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
            overall = score >= 0.6  # at least 3 of 5 elements present

            results.append(ClaimElementsResult(
                section=section,
                checks=checks,
                overall_pass=overall,
                score=round(score, 2),
            ))

        return results
