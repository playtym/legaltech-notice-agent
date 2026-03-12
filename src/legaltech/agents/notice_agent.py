from __future__ import annotations

import logging
import re
from datetime import datetime

from legaltech.agents.arbitration_agent import ArbitrationCheckResult
from legaltech.agents.claim_elements_agent import ClaimElementsResult
from legaltech.agents.escalation_agent import EscalationStrategy
from legaltech.agents.jurisdiction_agent import JurisdictionResult
from legaltech.agents.legal_analysis_agent import LegalAnalysis
from legaltech.agents.limitation_agent import LimitationResult
from legaltech.agents.respondent_id_agent import RespondentIdentity
from legaltech.agents.evidence_scoring_agent import EvidenceScore
from legaltech.agents.tc_counter_agent import TCCounterResult
from legaltech.schemas import ComplaintInput, CompanyProfile, ContactInfo, PolicyEvidence
from legaltech.services.llm import LLMService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a senior Indian consumer rights advocate drafting a formal Legal Notice \
under the Consumer Protection Act, 2019 and all applicable Indian statutes.

ROLE: You are NOT writing a polite complaint letter. You are writing a formal legal \
document that will be served on the respondent company. Write like a seasoned consumer \
lawyer who has won hundreds of cases before the District Commission, State Commission, \
and NCDRC.

TONE & STYLE:
- Authoritative, precise, and assertive — not aggressive or threatening
- Every factual claim must be tied to a specific legal provision
- Cite exact statutory sections (not vague references)
- Anticipate and preemptively dismantle the company's likely T&C defenses
- Use the structure and language of real Indian legal notices
- Address the respondent in second person ("you", "your company")
- Maintain legal formality throughout

MANDATORY SECTIONS (numbered, in this order):
1. Header: "LEGAL NOTICE" with date, addressee (company name, registered office, email), \
   respondent identification (CIN, LLPIN if available), sender details
2. Introduction: Assert consumer status under CPA 2019 §2(7), basis of notice
3. Statement of facts: Narrate the facts with lawyerly precision
4. Chronology of events: Date-wise account establishing continuing cause of action
5. Documentary evidence: List all evidence that will be produced
6. Legal basis: Cite EVERY applicable statutory provision with bare-act text verbatim. \
   Explain WHY each provision is attracted by the respondent's conduct.
7. Element-by-element claim analysis: Show which elements are satisfied per section
8. Preemptive rebuttal of T&C defenses (if any found): This is the KILLER section. \
   Quote the company's own T&C clause, then demolish it with statutory override + precedent.
9. Arbitration clause rebuttal (if applicable): Cite Emaar MGF v. Aftab Singh (2019) 12 SCC 1
10. Spirit of law and reasonableness
11. Limitation period assertion
12. Jurisdiction determination
13. Demand and relief sought: Be specific — exact amount, remedy, + mental agony compensation
14. ESCALATION STRATEGY — THIS IS THE MOST POWERFUL SECTION. List every specific \
   regulatory complaint, government portal filing, and reputational action the complainant \
   WILL take if the notice is not complied with. Name the exact regulator, portal, or body. \
   Frame each escalation as a STATEMENT OF INTENT, not a threat — e.g. "The complainant shall \
   simultaneously file a complaint with the RBI Ombudsman under the Integrated Ombudsman Scheme 2021" \
   or "A formal Grievance shall be lodged on the CPGRAMS portal (pgportal.gov.in) tracked by the PMO". \
   Include the director personal liability warning. Include the CC / multi-stakeholder service list. \
   The goal: make the company's legal team realize that ignoring this notice will trigger regulatory, \
   reputational, and compliance consequences from MULTIPLE directions simultaneously — \
   making resolution the cheapest and most rational option.
15. Consequence of non-compliance: Specific commission filing + the full escalation strategy above
16. Reservation of rights (including criminal remedies if applicable)
17. Mode of service (Email to official company email + copies to all CC stakeholders via email)
18. Signature block

CRITICAL RULES:
- Use the exact section citations and bare-act text provided in the brief — do NOT hallucinate sections
- If the brief contains CLAUDE-RESEARCHED PROVISIONS (marked as such), cite them with the same \
  authority as rule-engine provisions — Claude has identified them as applicable law
- Never print placeholder text such as "To be verified via MCA Portal" or similar verification placeholders
- If CIN/LLPIN/registered office details are unavailable, omit those fields entirely from the final notice
- If no T&C/policy text is available, do NOT mention this absence; proceed with primary-objection reasonableness analysis
- Include ALL T&C counter-arguments provided — do not skip any
- Include ALL escalation tactics provided in the brief — each one adds pressure
- Include the arbitration rebuttal if an arbitration clause was found
- Quantify the cure period as specified in the brief
- The notice must be in ENGLISH only
- Output ONLY the notice text — no preamble, no markdown, no explanations
"""


class NoticeDraftAgent:
    """Drafts a legal notice using Claude as the core writer.

    The notice is NOT a polite customer complaint — it is a formal legal
    document that preemptively dismantles anticipated T&C defenses,
    cites binding statutory provisions and precedent, and creates a
    credible litigation threat that compels resolution.
    """

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm

    async def run(
        self,
        complaint: ComplaintInput,
        normalized_issue: str,
        company: CompanyProfile,
        contacts: list[ContactInfo],
        policies: list[PolicyEvidence],
        legal_analysis: LegalAnalysis,
        claim_results: list[ClaimElementsResult],
        respondent_identity: RespondentIdentity | None = None,
        evidence_score: EvidenceScore | None = None,
        limitation_result: LimitationResult | None = None,
        arbitration_result: ArbitrationCheckResult | None = None,
        jurisdiction_result: JurisdictionResult | None = None,
        tc_counter_result: TCCounterResult | None = None,
        cure_days: int = 15,
        cure_rationale: str = "15 days (standard)",
        follow_up_answers: dict[str, str] | None = None,
        escalation_strategy: EscalationStrategy | None = None,
    ) -> str:
        brief = self._build_brief(
            complaint=complaint,
            normalized_issue=normalized_issue,
            company=company,
            contacts=contacts,
            policies=policies,
            legal_analysis=legal_analysis,
            claim_results=claim_results,
            respondent_identity=respondent_identity,
            evidence_score=evidence_score,
            limitation_result=limitation_result,
            arbitration_result=arbitration_result,
            jurisdiction_result=jurisdiction_result,
            tc_counter_result=tc_counter_result,
            cure_days=cure_days,
            cure_rationale=cure_rationale,
            follow_up_answers=follow_up_answers,
            escalation_strategy=escalation_strategy,
        )

        notice_text = await self.llm.complete_text(_SYSTEM_PROMPT, brief)
        return self._sanitize_notice(notice_text)

    @staticmethod
    def _sanitize_notice(notice_text: str) -> str:
        """Remove known placeholder artifacts that should never be shown to users."""
        cleaned_lines: list[str] = []
        banned = [
            re.compile(r"registered\s+office\s+address\s*:\s*to\s+be\s+verified\s+via\s+mca\s+portal", re.I),
            re.compile(r"cin\s*/\s*llpin\s*:\s*to\s+be\s+verified\s+via\s+mca\s+portal", re.I),
            re.compile(r"to\s+be\s+verified\s+via\s+mca\s+portal", re.I),
        ]
        for line in notice_text.splitlines():
            if any(p.search(line) for p in banned):
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    @staticmethod
    def _strategy_hints(
        complaint: ComplaintInput,
        evidence_score: EvidenceScore | None,
        arbitration_result: ArbitrationCheckResult | None,
        tc_counter_result: TCCounterResult | None,
    ) -> list[str]:
        hints: list[str] = []
        issue = complaint.issue_summary.lower()
        desired = complaint.desired_resolution.lower()

        if "refund" in issue or "refund" in desired:
            hints.append(
                "Prioritize a quantified refund demand first, then add compensation and litigation costs as secondary relief."
            )
        if "replacement" in issue or "replace" in desired:
            hints.append(
                "Frame replacement as an alternative remedy with strict timeline, while preserving right to full refund if non-compliance continues."
            )
        if len(complaint.timeline) < 2:
            hints.append(
                "Strengthen chronology by anchoring at least one concrete transaction date and one follow-up/escalation date in the facts section."
            )
        if not complaint.evidence:
            hints.append(
                "Add a short preservation demand requiring respondent to retain call logs, chat logs, order logs, and ticket history pending adjudication."
            )
        if evidence_score and evidence_score.contradictions:
            hints.append(
                "Avoid overclaiming disputed facts; explicitly rely on documentary points with highest consistency score to maintain credibility."
            )
        if tc_counter_result and tc_counter_result.counters:
            hints.append(
                "In rebuttal section, quote each defense clause verbatim before applying statutory override; this improves enforceability and persuasion."
            )
        if arbitration_result and arbitration_result.clauses_found:
            hints.append(
                "Keep arbitration rebuttal concise and place it immediately after T&C rebuttal to prevent forum-deflection by respondent counsel."
            )
        if "mental agony" in desired or "harassment" in issue:
            hints.append(
                "State compensation for harassment as proportionate and evidence-linked to avoid appearing speculative."
            )
        return hints

    def _build_brief(
        self,
        complaint: ComplaintInput,
        normalized_issue: str,
        company: CompanyProfile,
        contacts: list[ContactInfo],
        policies: list[PolicyEvidence],
        legal_analysis: LegalAnalysis,
        claim_results: list[ClaimElementsResult],
        respondent_identity: RespondentIdentity | None,
        evidence_score: EvidenceScore | None,
        limitation_result: LimitationResult | None,
        arbitration_result: ArbitrationCheckResult | None,
        jurisdiction_result: JurisdictionResult | None,
        tc_counter_result: TCCounterResult | None,
        cure_days: int,
        cure_rationale: str,
        follow_up_answers: dict[str, str] | None = None,
        escalation_strategy: EscalationStrategy | None = None,
    ) -> str:
        """Build the comprehensive brief that Claude uses to draft the notice."""
        today = datetime.utcnow().date().isoformat()
        company_label = company.legal_name or company.brand_name or "the company"
        primary_contact = contacts[0].email if contacts else "[official-email-not-found]"

        b: list[str] = []
        b.append("=" * 60)
        b.append("LEGAL NOTICE DRAFTING BRIEF")
        b.append("=" * 60)

        # ── Date ─────────────────────────────────────────────────────
        b.append(f"\nDate for notice: {today}")

        # ── Complainant ──────────────────────────────────────────────
        b.append(f"\n## COMPLAINANT (sender)")
        b.append(f"Name: {complaint.complainant.full_name}")
        b.append(f"Email: {complaint.complainant.email}")
        if complaint.complainant.phone:
            b.append(f"Phone: {complaint.complainant.phone}")
        if complaint.complainant.address:
            b.append(f"Address: {complaint.complainant.address}")

        # ── Respondent (company) ─────────────────────────────────────
        b.append(f"\n## RESPONDENT (addressee)")
        b.append(f"Company: {company_label}")
        if company.domain:
            b.append(f"Website: {company.domain}")
        b.append(f"Primary contact email: {primary_contact}")
        if respondent_identity:
            if respondent_identity.cin:
                b.append(f"CIN: {respondent_identity.cin}")
            if respondent_identity.llpin:
                b.append(f"LLPIN: {respondent_identity.llpin}")
            if respondent_identity.registered_name:
                b.append(f"Registered Name: {respondent_identity.registered_name}")
            if respondent_identity.registered_office:
                b.append(f"Registered Office: {respondent_identity.registered_office}")
            if respondent_identity.grievance_officer_name:
                b.append(f"Grievance Officer: {respondent_identity.grievance_officer_name}")
            if respondent_identity.grievance_officer_email:
                b.append(f"Grievance Officer Email: {respondent_identity.grievance_officer_email}")
            for flag in respondent_identity.verification_flags:
                b.append(f"[VERIFY] {flag}")
        else:
            b.append(
                "Respondent identity details could not be conclusively extracted from the available "
                "public website sources. If applicable, frame this as non-compliance with mandatory "
                "e-commerce disclosure obligations under E-Commerce Rules 2020 Rule 4, without using placeholders."
            )

        # ── Facts ────────────────────────────────────────────────────
        b.append(f"\n## COMPLAINT SUMMARY (normalized)")
        b.append(normalized_issue)

        b.append(f"\n## ORIGINAL ISSUE (as stated by complainant)")
        b.append(complaint.issue_summary)

        b.append(f"\n## DESIRED RESOLUTION")
        b.append(complaint.desired_resolution)

        # ── Timeline ─────────────────────────────────────────────────
        b.append(f"\n## TIMELINE OF EVENTS")
        if complaint.timeline:
            for t in complaint.timeline:
                b.append(f"- {t}")
        else:
            b.append("[No timeline provided — note this as a gap]")

        # ── Evidence ─────────────────────────────────────────────────
        b.append(f"\n## EVIDENCE AVAILABLE")
        if complaint.evidence:
            for e in complaint.evidence:
                b.append(f"- {e}")
        else:
            b.append("[No evidence listed — should request documentary proof]")

        # ── Evidence quality score ───────────────────────────────────
        if evidence_score:
            b.append(f"\n## EVIDENCE QUALITY ASSESSMENT")
            b.append(f"Overall score: {evidence_score.overall_score}")
            b.append(f"Completeness: {evidence_score.completeness_score}")
            b.append(f"Consistency: {evidence_score.consistency_score}")
            if evidence_score.contradictions:
                b.append("Contradictions:")
                for c in evidence_score.contradictions:
                    b.append(f"  - {c}")
            if evidence_score.gaps:
                b.append("Gaps:")
                for g in evidence_score.gaps:
                    b.append(f"  - {g}")

        # ── Statutory sections attracted ─────────────────────────────
        b.append(f"\n## STATUTORY PROVISIONS ATTRACTED (use ALL of these)")
        for sec in legal_analysis.plausible_sections:
            legacy = f" (erstwhile {sec.legacy_reference})" if sec.legacy_reference else ""
            source_tag = " [CLAUDE-RESEARCHED]" if not sec.trigger_keywords else ""
            b.append(f"- {sec.act}, {sec.section}{legacy}: {sec.title}{source_tag}")
            b.append(f"  Why applicable: {sec.why_relevant}")

        if legal_analysis.used_llm_research:
            b.append("\nNOTE: Sections marked [CLAUDE-RESEARCHED] were identified by AI legal research ")
            b.append("because this case involves areas beyond the rule engine's pre-mapped sections. ")
            b.append("Cite them with the same authority — they are valid Indian statutory provisions.")

        # ── Bare-act text (verbatim — must be used exactly) ──────────
        b.append(f"\n## BARE-ACT TEXT (cite verbatim in the notice)")
        for entry in legal_analysis.bare_act_entries:
            b.append(f"[{entry.act}, {entry.section}]: \"{entry.bare_text}\"")
            if entry.amendment_note:
                b.append(f"  Amendment: {entry.amendment_note}")

        # ── Claim element analysis ───────────────────────────────────
        b.append(f"\n## CLAIM ELEMENT ANALYSIS")
        for cr in claim_results:
            status = "PASS" if cr.overall_pass else "PARTIAL"
            b.append(f"- {cr.section.act}, {cr.section.section}: {status} (score: {cr.score:.1f})")
            for check in cr.checks:
                sym = "✓" if check.satisfied else "✗"
                b.append(f"    {sym} {check.element}: {check.reasoning}")

        # ── T&C Counter-arguments (MANDATORY — include ALL) ──────────
        if tc_counter_result and tc_counter_result.counters:
            b.append(f"\n## T&C COUNTER-ARGUMENTS (include ALL in notice — this is critical)")
            for counter in tc_counter_result.counters:
                b.append(f"\nDefense: {counter.defense_clause}")
                b.append(f"Their clause: \"{counter.clause_excerpt}\"")
                b.append(f"Counter-argument: {counter.legal_counter}")
                b.append(f"Statutory basis: {counter.statutory_basis}")
                b.append(f"Precedent: {counter.precedent_note}")
        else:
            b.append(f"\n## T&C COUNTER-ARGUMENTS")
            b.append(
                "Build a strong objection-rebuttal analysis from the primary dispute facts and respondent conduct. "
                "Do not mention missing T&C/policy pages. Focus on reasonableness, proportionality, burden of proof, "
                "and unfair trade practice standards under CPA 2019."
            )

        # ── Arbitration clause ───────────────────────────────────────
        if arbitration_result and arbitration_result.clauses_found:
            b.append(f"\n## ARBITRATION CLAUSE DETECTED (must rebut in notice)")
            for clause in arbitration_result.clauses_found:
                b.append(f"Clause: \"{clause.text_excerpt}\"")
                b.append(f"Type: {clause.clause_type}")
            b.append("Legal override: CPA 2019 §2(7)(ii) + Emaar MGF v. Aftab Singh (2019) 12 SCC 1")
        elif arbitration_result:
            b.append(f"\n## ARBITRATION: No arbitration clause found")

        # ── Limitation ───────────────────────────────────────────────
        b.append(f"\n## LIMITATION PERIOD")
        if limitation_result:
            b.append(limitation_result.warning)
        else:
            b.append("Within statutory limitation period")

        # ── Jurisdiction ─────────────────────────────────────────────
        b.append(f"\n## JURISDICTION")
        if jurisdiction_result:
            b.append(f"Forum: {jurisdiction_result.forum}")
            b.append(f"Pecuniary: {jurisdiction_result.pecuniary_basis}")
            b.append(f"Territorial: {jurisdiction_result.territorial_basis}")
            b.append(f"Section: {jurisdiction_result.section_reference}")
        else:
            b.append("District Commission (default)")

        # ── Cure period ──────────────────────────────────────────────
        b.append(f"\n## CURE PERIOD")
        b.append(f"{cure_days} days — {cure_rationale}")

        # ── Policy excerpts scraped ──────────────────────────────────
        if policies:
            b.append(f"\n## COMPANY POLICIES/T&C SCRAPED ({len(policies)} pages)")
            for policy in policies[:5]:
                b.append(f"[{policy.source_url}]: {policy.excerpt[:300]}")

        # ── Follow-up answers from user ──────────────────────────────
        if follow_up_answers:
            b.append(f"\n## ADDITIONAL INFORMATION FROM COMPLAINANT (follow-up answers)")
            for qid, answer in follow_up_answers.items():
                b.append(f"Q {qid}: {answer}")
            b.append("\nIMPORTANT: Incorporate ALL of the above answers into the notice facts, evidence, and arguments.")

        # ── Strategic drafting hints ────────────────────────────────
        strategy_hints = self._strategy_hints(
            complaint=complaint,
            evidence_score=evidence_score,
            arbitration_result=arbitration_result,
            tc_counter_result=tc_counter_result,
        )
        if strategy_hints:
            b.append("\n## STRATEGIC DRAFTING HINTS (priority)")
            for hint in strategy_hints:
                b.append(f"- {hint}")

        # ── Escalation strategy (pressure tactics) ───────────────────
        if escalation_strategy and escalation_strategy.tactics:
            b.append(f"\n## ESCALATION / PRESSURE TACTICS (include ALL — this makes the notice resolve the dispute)")
            b.append(f"Severity level: {escalation_strategy.severity_level}")
            b.append(f"Summary: {escalation_strategy.summary}")
            for i, tactic in enumerate(escalation_strategy.tactics, 1):
                b.append(f"\n### Tactic {i}: {tactic.tactic}")
                b.append(f"Action: {tactic.action}")
                b.append(f"Target: {tactic.target_authority}")
                b.append(f"Legal basis: {tactic.legal_basis}")
                b.append(f"Impact: {tactic.impact_description}")
            b.append(
                "\nINSTRUCTION: Weave ALL of the above tactics into the Escalation Strategy, "
                "Consequence of Non-Compliance, and Reservation of Rights sections of the notice. "
                "The CC / multi-stakeholder list should appear in the Mode of Service section. "
                "Each tactic should read as a STATEMENT OF INTENT — not a threat — "
                "e.g. 'The complainant shall file a complaint with [authority] under [section]'."
            )

        # ── Spirit of law ────────────────────────────────────────────
        b.append(f"\n## SPIRIT OF LAW")
        b.append(legal_analysis.spirit_of_law_view)
        b.append(legal_analysis.reasonableness_view)

        return "\n".join(b)
