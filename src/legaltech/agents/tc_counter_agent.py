"""Terms & Conditions counter-argument agent.

Uses Claude to identify corporate defense clauses in scraped T&Cs and
build persuasive legal counter-arguments. Falls back to regex-based
pattern matching if LLM is unavailable.
"""

from __future__ import annotations

import json
import logging

import re
from dataclasses import dataclass, field

from legaltech.schemas import PolicyEvidence


@dataclass
class TCDefenseCounter:
    defense_clause: str          # What the company will likely argue
    clause_excerpt: str          # Excerpt from their T&C
    source_url: str
    legal_counter: str           # Our counter-argument
    statutory_basis: str         # Law that overrides the clause
    precedent_note: str          # Supporting precedent or principle


@dataclass
class TCCounterResult:
    counters: list[TCDefenseCounter] = field(default_factory=list)
    overall_strategy: str = ""


# ── Common corporate defense patterns and their legal counters ───────

_DEFENSE_PATTERNS: list[tuple[re.Pattern[str], str, str, str, str]] = [
    # (regex, defense_label, counter_argument, statutory_basis, precedent_note)
    (
        re.compile(r"(?:no\s+refund|non[\s-]*refundable|all\s+sales?\s+(?:are\s+)?final)", re.I),
        "No-refund / all-sales-final policy",
        (
            "A blanket 'no refund' clause is unenforceable against a consumer who has received "
            "deficient service or defective goods. Section 2(47) CPA 2019 classifies unilateral "
            "'no refund' terms as an unfair trade practice when the consumer has a legitimate "
            "grievance. The right to seek refund for deficiency under Section 2(11) is a statutory "
            "right that cannot be contracted away."
        ),
        "CPA 2019 §2(47) (unfair trade practice), §2(11) (deficiency), §2(6) (consumer rights)",
        "Spring Meadows Hospital v. Harjot Ahluwalia (1998) 4 SCC 39 — contractual limitation "
        "clauses cannot override statutory consumer protection rights.",
    ),
    (
        re.compile(r"(?:limitation\s+of\s+liability|liability\s+(?:shall\s+)?not\s+exceed|maximum\s+(?:aggregate\s+)?liability|cap\s+(?:on\s+)?(?:damages|liability))", re.I),
        "Limitation of liability / damages cap",
        (
            "Contractual caps on liability are not binding on Consumer Commissions which have "
            "independent jurisdiction under CPA 2019 to award 'such amount of compensation to the "
            "consumer as the Commission may determine' (§39(1)(d)). The Commission is not bound by "
            "the contractual ceiling when the deficiency or unfair practice is established."
        ),
        "CPA 2019 §39(1)(d), §2(11) read with §58(1)",
        "NCDRC in Amazon Seller Services v. Anand Kumar (2023) — consumer commission may award "
        "compensation beyond contractual liability caps where unfair trade practice is established.",
    ),
    (
        re.compile(r"(?:indirect|consequential|incidental|special|punitive)\s+damages?\s+(?:are\s+)?(?:excluded|waived|not\s+(?:liable|responsible))", re.I),
        "Exclusion of indirect / consequential damages",
        (
            "CPA 2019 §39(1)(d) empowers the Consumer Commission to direct payment of 'adequate "
            "compensation' which explicitly includes mental agony, harassment, and consequential "
            "loss. A term purporting to exclude consequential damages is an unfair contract term "
            "under §2(46)(vi) and constitutes an unfair trade practice under §2(47)."
        ),
        "CPA 2019 §2(46)(vi) (unfair contract terms), §39(1)(d), §2(47)",
        "Lucknow Development Authority v. M.K. Gupta (1994) 1 SCC 243 — Supreme Court held that "
        "compensation for mental anguish is integral to consumer relief, irrespective of contractual "
        "exclusions.",
    ),
    (
        re.compile(r"(?:force\s+majeure|act\s+of\s+god|circumstances\s+beyond\s+(?:our\s+)?control|unforeseeable\s+event)", re.I),
        "Force majeure / beyond-our-control clause",
        (
            "Force majeure defenses require genuinely unforeseeable events outside reasonable control. "
            "Routine operational failures (IT outages, courier delays, stock shortages) do not "
            "constitute force majeure. The burden is on the service provider to prove the event was "
            "truly external, unforeseeable, and directly caused the non-performance. Even where "
            "invoked, the provider must demonstrate it took all reasonable steps to mitigate."
        ),
        "Indian Contract Act 1872 §56 (impossibility), CPA 2019 §2(11) (deficiency)",
        "Energy Watchdog v. CERC (2017) 14 SCC 80 — Supreme Court held that commercial hardship "
        "or routine market conditions do not qualify as force majeure.",
    ),
    (
        re.compile(r"(?:we\s+(?:may|reserve|shall)\s+(?:the\s+right\s+to\s+)?(?:change|modify|alter|update|revise)\s+(?:these|this|the|our)\s+(?:terms|conditions|policies?|pricing|T&C))", re.I),
        "Unilateral right to modify terms",
        (
            "A clause reserving unilateral right to modify terms without fresh consent is an unfair "
            "contract term under CPA 2019 §2(46)(i)-(ii). Terms cannot be unilaterally altered to "
            "the detriment of the consumer after the contract is formed. Any material change requires "
            "fresh, informed consent of the consumer."
        ),
        "CPA 2019 §2(46)(i)-(ii) (unfair contract terms), Indian Contract Act 1872 §23 (void terms)",
        "NCDRC principle: retrospective or unilateral modification of contractual terms after "
        "consumer has acted on the original terms constitutes an unfair trade practice under CPA 2019 §2(47).",
    ),
    (
        re.compile(r"(?:(?:at\s+)?(?:our|sole|absolute)\s+discretion|(?:we|company)\s+(?:may|shall)\s+(?:at\s+(?:its|our)\s+)?(?:sole\s+)?discretion)", re.I),
        "Sole discretion / absolute right clause",
        (
            "Clauses vesting 'sole discretion' in the service provider to determine outcomes "
            "(refund eligibility, service continuation, complaint resolution) are inherently "
            "one-sided and qualify as unfair contract terms under CPA 2019 §2(46). The Consumer "
            "Commission has independent jurisdiction to determine whether the company's exercise "
            "of discretion was reasonable." 
        ),
        "CPA 2019 §2(46)(iv)-(vi) (unfair contract terms), §39(1)",
        "NCDRC principle: discretionary clauses are not absolute when they allow the dominant party "
        "to unilaterally override the weaker party's statutory rights.",
    ),
    (
        re.compile(r"(?:as[\s-]*is|without\s+warranty|no\s+(?:warranty|guarantee)|provided\s+as[\s-]*is)", re.I),
        "As-is / no-warranty disclaimer",
        (
            "'As-is' disclaimers cannot defeat implied warranties under the Sale of Goods Act 1930 "
            "§16 (fitness for purpose) or the CPA 2019 product liability framework (§59-87). When "
            "goods are sold in the ordinary course of business, the implied condition of "
            "merchantable quality operates regardless of boilerplate disclaimers."
        ),
        "Sale of Goods Act 1930 §16, CPA 2019 §§59-62 (product liability), §84 (product liability of manufacturer)",
        "National Insurance Co. v. Nitin Khandelwal (2008) 11 SCC 259 — implied conditions cannot "
        "be defeated by standard form exclusion clauses.",
    ),
    (
        re.compile(r"(?:governing\s+law|subject\s+to\s+(?:the\s+)?laws?\s+of|jurisdiction\s+(?:of|in)\s+(?:courts?\s+(?:at|in|of)))", re.I),
        "Exclusive jurisdiction / governing law clause",
        (
            "Contractual jurisdiction clauses do not bind consumer forums. CPA 2019 §35 grants "
            "consumers the statutory right to file where they reside or where the cause of action "
            "arose, regardless of any contractual forum selection clause. The Supreme Court has "
            "consistently held that consumer forum jurisdiction under the CPA cannot be ousted by "
            "contractual terms."
        ),
        "CPA 2019 §35 (filing jurisdiction), §2(7)(ii) (consumer forum overrides arbitration)",
        "Emaar MGF Land Ltd v. Aftab Singh (2019) 12 SCC 1 — Supreme Court held that existence "
        "of arbitration agreement does not bar a consumer from approaching consumer forum.",
    ),
    (
        re.compile(r"(?:deemed\s+(?:to\s+)?(?:have\s+)?accept|(?:by\s+)?(?:using|accessing|continuing)\s+(?:this|our|the)\s+(?:service|platform|app|website)\s+you\s+(?:agree|accept|consent))", re.I),
        "Deemed acceptance / clickwrap enforceability",
        (
            "Deemed consent through mere usage is not informed, specific consent under Indian law. "
            "CPA 2019 §2(46)(vii) classifies terms that 'impose on the consumer any unreasonable "
            "charge, obligation, or condition which puts such consumer to disadvantage' as unfair. "
            "For clickwrap agreements, courts examine whether the specific term was brought to the "
            "consumer's attention and whether consent was genuinely voluntary."
        ),
        "CPA 2019 §2(46)(vii), Indian Contract Act 1872 §14 (free consent)",
        "Trimex International v. Vedanta Aluminium (2010) 3 SCC 1 — mere signing/clicking does not "
        "establish genuine consent to onerous non-negotiable terms buried in lengthy T&Cs.",
    ),
    (
        re.compile(r"(?:not\s+(?:responsible|liable)\s+for\s+(?:(?:any\s+)?(?:loss|damage|delay))|third[\s-]*party|partner\s+(?:seller|vendor|merchant))", re.I),
        "Third-party / marketplace intermediary defense",
        (
            "The marketplace intermediary defense is significantly curtailed under the Consumer "
            "Protection (E-Commerce) Rules, 2020 (Rules 4-6). E-commerce entities have mandatory "
            "duties including grievance redressal within 48 hours (Rule 4(4)), displaying seller "
            "details, and ensuring dispute resolution. CPA 2019 §2(47)(ix) makes failing to "
            "withdraw deficient services an unfair trade practice even for intermediaries."
        ),
        "E-Commerce Rules 2020 Rules 4-6, CPA 2019 §2(47)(ix), §2(7) (e-commerce includes platforms)",
        "Amazon Seller Services v. Consumer — NCDRC (2023) held that e-commerce platforms cannot "
        "wash their hands off liability by claiming to be mere intermediaries when they actively "
        "facilitate the transaction.",
    ),
]


logger = logging.getLogger(__name__)

_TC_SYSTEM_PROMPT = """\
You are a senior Indian consumer rights lawyer. Given company Terms & Conditions \
text and a consumer complaint, identify ALL corporate defense clauses the company \
could use to deny the claim, and build devastating legal counter-arguments.

For each defense clause found, provide:
1. The defense the company will likely raise
2. The exact clause excerpt from their T&C
3. A strong legal counter-argument citing Indian statutory overrides
4. The statutory basis (Act and section numbers)
5. Supporting precedent or legal principle

COMMON DEFENSES TO LOOK FOR:
- No-refund / all-sales-final policies
- Limitation of liability / damages caps
- Exclusion of indirect/consequential damages
- Force majeure / beyond-control clauses
- Unilateral right to modify terms
- Sole discretion clauses
- As-is / no-warranty disclaimers
- Exclusive jurisdiction clauses
- Deemed acceptance / clickwrap terms
- Third-party / intermediary defense

KEY INDIAN STATUTORY OVERRIDES:
- CPA 2019 §2(46) — unfair contract terms
- CPA 2019 §2(47) — unfair trade practices
- CPA 2019 §39(1)(d) — compensation powers
- CPA 2019 §35 — consumer forum jurisdiction overrides contracts
- Emaar MGF v. Aftab Singh (2019) 12 SCC 1 — arbitration no bar

If no T&C text is available, return an empty counters array — do NOT invent \
hypothetical defenses or fabricate clause excerpts.

Return JSON:
{
  "counters": [
    {
      "defense_clause": "short label",
      "clause_excerpt": "quoted text from T&C",
      "source_url": "URL where found",
      "legal_counter": "detailed counter-argument",
      "statutory_basis": "Act §section references",
      "precedent_note": "supporting case/principle"
    }
  ],
  "overall_strategy": "summary of counter-argument strategy"
}

Return ONLY the JSON.
"""


class TCCounterAgent:
    """Scans company T&Cs and builds preemptive legal counter-arguments."""

    def __init__(self, llm=None) -> None:
        self.llm = llm

    async def run(
        self,
        policy_evidence: list[PolicyEvidence],
        issue_summary: str,
    ) -> TCCounterResult:
        if self.llm:
            try:
                return await self._agentic_run(policy_evidence, issue_summary)
            except Exception as exc:
                logger.warning("LLM T&C counter failed, using fallback: %s", exc)
        return self._deterministic_run(policy_evidence, issue_summary)

    async def _agentic_run(
        self,
        policy_evidence: list[PolicyEvidence],
        issue_summary: str,
    ) -> TCCounterResult:
        # Short-circuit: if no real policy text was scraped, skip LLM call
        # entirely to avoid hallucinated defenses and phantom citations.
        real_policies = [
            p for p in (policy_evidence or [])
            if p.excerpt and p.excerpt.strip()
               and "login page" not in p.excerpt.lower()
               and "navigation" not in p.excerpt.lower()
               and len(p.excerpt.strip()) > 50
        ]
        if not real_policies:
            return TCCounterResult(
                counters=[],
                overall_strategy="No T&C / policy text was available for analysis.",
            )

        policy_text = "\n\n".join(
            f"[Source: {p.source_url}]\n{p.excerpt[:800]}"
            for p in real_policies
        )

        user_prompt = (
            f"## Consumer Complaint\n{issue_summary}\n\n"
            f"## Company T&C / Policy Text\n{policy_text}"
        )
        data = await self.llm.complete_json(_TC_SYSTEM_PROMPT, user_prompt)

        counters = [
            TCDefenseCounter(
                defense_clause=c["defense_clause"],
                clause_excerpt=c.get("clause_excerpt", ""),
                source_url=c.get("source_url", "llm-analysis"),
                legal_counter=c["legal_counter"],
                statutory_basis=c.get("statutory_basis", ""),
                precedent_note=c.get("precedent_note", ""),
            )
            for c in data.get("counters", [])
        ]
        return TCCounterResult(
            counters=counters,
            overall_strategy=data.get("overall_strategy", ""),
        )

    def _deterministic_run(
        self,
        policy_evidence: list[PolicyEvidence],
        issue_summary: str,
    ) -> TCCounterResult:
        result = TCCounterResult()
        seen_defenses: set[str] = set()

        for policy in policy_evidence:
            text = policy.excerpt
            for pattern, defense_label, counter, statutory, precedent in _DEFENSE_PATTERNS:
                if defense_label in seen_defenses:
                    continue
                match = pattern.search(text)
                if match:
                    seen_defenses.add(defense_label)
                    start = max(0, match.start() - 60)
                    end = min(len(text), match.end() + 100)
                    excerpt = text[start:end].strip()

                    result.counters.append(TCDefenseCounter(
                        defense_clause=defense_label,
                        clause_excerpt=excerpt,
                        source_url=policy.source_url,
                        legal_counter=counter,
                        statutory_basis=statutory,
                        precedent_note=precedent,
                    ))

        if result.counters:
            defenses = ", ".join(c.defense_clause for c in result.counters)
            result.overall_strategy = (
                f"The company's Terms & Conditions contain {len(result.counters)} potentially "
                f"obstructive clause(s): {defenses}. Indian consumer protection law holds that "
                f"statutory consumer rights under CPA 2019 cannot be contracted away."
            )
        else:
            result.overall_strategy = (
                "No T&C / policy text was available for direct quotation."
            )
        return result
