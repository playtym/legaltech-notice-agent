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

# ── Case-type specialization database ────────────────────────────────

_CASE_TYPE_SIGNALS: dict[str, tuple[str, ...]] = {
    "ecommerce": ("order", "delivery", "refund", "product", "amazon", "flipkart", "myntra",
                  "meesho", "snapdeal", "e-commerce", "ecommerce", "online shopping",
                  "cart", "cod", "marketplace", "return", "replacement", "defective product"),
    "banking": ("bank", "loan", "emi", "credit card", "debit card", "upi", "wallet",
                "nbfc", "fintech", "neft", "rtgs", "imps", "razorpay", "paytm", "phonepe",
                "account", "transaction", "cheque", "overcharge", "interest"),
    "insurance": ("policy", "claim", "premium", "insurance", "irdai", "life insurance",
                  "health insurance", "motor insurance", "mediclaim", "cashless", "nominee",
                  "rejection", "repudiation"),
    "telecom": ("mobile", "sim", "recharge", "broadband", "jio", "airtel", "vodafone", "vi",
                "bsnl", "telecom", "network", "data plan", "porting", "trai", "internet"),
    "real_estate": ("flat", "apartment", "builder", "possession", "rera", "real estate",
                    "construction", "housing", "property", "developer", "registry"),
    "airline_travel": ("flight", "airline", "ticket", "booking", "cancellation", "airport",
                       "boarding", "indigo", "air india", "spicejet", "dgca", "travel", "hotel"),
    "food": ("food", "fssai", "expired", "contaminated", "restaurant", "zomato",
             "swiggy", "grocery", "bigbasket", "blinkit"),
    "automobile": ("car", "vehicle", "service center", "dealer", "warranty", "automobile",
                   "ev", "bike", "scooter"),
    "education": ("university", "college", "coaching", "edtech", "course", "admission",
                  "fee", "byju", "unacademy"),
    "healthcare": ("hospital", "doctor", "treatment", "medical", "clinic", "pharmacy",
                   "lab", "diagnosis", "surgery"),
}

_CASE_TYPE_STRATEGY: dict[str, str] = {
    "ecommerce": """\
CASE-TYPE STRATEGY — E-COMMERCE DISPUTE:
- Lead with E-Commerce Rules 2020 (Rule 4 disclosure obligations, Rule 5 seller duties, Rule 6 marketplace duties)
- If delivery failure: frame as breach of contract + deficiency in service + unfair trade practice triple combo
- If defective product: invoke strict product liability under CPA 2019 §§82-87 (manufacturer + seller + marketplace joint liability)
- If refund delayed: calculate interest from promise date, invoke §2(11) for deficiency, cite RBI guidelines on settlement timelines
- Highlight e-commerce intermediary's vicarious liability — they cannot hide behind "marketplace model"
- Reference CCPA powers (§§18-27) including product recall and penalties up to ₹50 lakh
- For high-value orders, emphasize that the complainant chose the platform BECAUSE of its representations""",
    "banking": """\
CASE-TYPE STRATEGY — BANKING/FINANCE DISPUTE:
- Lead with RBI Master Directions on Customer Service (2023 framework) and Integrated Ombudsman Scheme 2021
- If unauthorized debit: invoke RBI circular on zero liability (< 3 days reporting = full bank liability)
- If loan overcharge: calculate exact excess with amortization math, cite NBFC Master Directions on fair practices
- If credit card dispute: invoke RBI Master Direction on Credit Card Operations §14 (billing disputes)
- Emphasize personal liability of compliance officer for RBI regulation violations
- Reference Banking Codes and Standards Board of India (BCSBI) commitments as binding representations
- For UPI disputes: cite NPCI Dispute Resolution Mechanism timeline (T+5 days for credit back)
- Use bank's own charter of customer rights against them""",
    "insurance": """\
CASE-TYPE STRATEGY — INSURANCE DISPUTE:
- Lead with IRDAI (Protection of Policyholders' Interests) Regulations 2017
- If claim rejected: demand the EXACT rejection reason per Regulation 17(7), challenge vague rejections
- If delayed settlement: cite mandatory settlement timelines (30 days from last document per Reg 17(6))
- Invoke §4 of Insurance Act 1938 on utmost good faith — it binds the INSURER, not just the policyholder
- Reference IRDAI circular on rejection rates and insurers flagged for excessive rejections
- If pre-existing disease exclusion: challenge the definition scope per Regulation 2(d) and standard exclusion limits
- Invoke Section 45 (2-year contestability clause) — after 2 years, no policy can be repudiated on grounds of misstatement
- For mediclaim: cite IRDAI standardized exclusion list — company cannot exclude beyond listed items""",
    "telecom": """\
CASE-TYPE STRATEGY — TELECOM DISPUTE:
- Lead with TRAI Regulations — Quality of Service, Metering & Billing, Tariff transparency
- If overbilling: demand CDR (Call Detail Records) under TRAI direction, operator must provide within 7 days
- If network failure: cite TRAI QoS standards and the point-of-interconnection regulations
- If port-out blocked: invoke MNP Regulations — operator CANNOT block porting except 3 valid exceptions
- If unauthorized VAS charges: cite TRAI regulation on explicit consent for value-added services
- Reference telecom license conditions under §7 that mandate quality standards
- Emphasize TRAI complaint mechanism on trai.gov.in and appeal to TDSAT under TRAI Act §14
- For broadband: cite TRAI recommendations on minimum speed guarantees""",
    "real_estate": """\
CASE-TYPE STRATEGY — REAL ESTATE DISPUTE:
- Lead with RERA 2016 — this is the PRIMARY statute, CPA is supplementary
- If delayed possession: invoke §18 RERA (interest at SBI MCLR + 2%, or prescribed rate)
- If specification deviation: cite §14 (adherence to sanctioned plans) and §§19(3)-19(4)
- File simultaneously with RERA Authority AND Consumer Commission — dual remedy is permitted per Imperia Structures v. Anil Patni (2020) 10 SCC 783
- Calculate per-day delay compensation using RERA formula: agreement value × prescribed rate ÷ 365
- Challenge one-sided force majeure clauses — buyer-builder agreement cannot override RERA entitlements
- Reference specific State RERA orders against the same builder (check relevant State RERA website)
- Invoke §7A (compensation for delay) and §8 (formation of association entitlement)""",
    "airline_travel": """\
CASE-TYPE STRATEGY — AIRLINE/TRAVEL DISPUTE:
- Lead with DGCA CAR Section 3, Series M, Part IV (facilities to passengers by airlines due to denied boarding, cancellation, and delays)
- If flight cancelled: cite mandatory compensation — up to ₹20,000 for domestic (> 2 hrs delay) per DGCA
- If denied boarding: invoke overbooked flight compensation rules — 200%/400% of ticket per DGCA
- Reference Montreal Convention for international routes (SDR-based compensation for delays/damage)
- If hotel booking: cite Hotel & Restaurant Approval and Classification Committee (HRACC) rules
- For travel agent: cite Indian Contract Act §§182-238 (agency liability) + CPA 2019 deficiency
- File complaint on AirSewa portal (airsewa.gov.in) — tracked by Ministry of Civil Aviation
- Emphasize passenger charter of rights published by DGCA""",
    "food": """\
CASE-TYPE STRATEGY — FOOD/FMCG DISPUTE:
- Lead with Food Safety and Standards Act 2006 (FSSA) and FSSAI Regulations
- If adulterated/contaminated: invoke §§50-59 FSSA (penalties including imprisonment for unsafe food)
- If expired product sold: cite FSSAI labeling regulations + CPA 2019 unfair trade practice
- Reference food operator's FSSAI license number — non-display itself is a violation
- File complaint with local Food Safety Officer in addition to consumer commission
- For food delivery platforms (Zomato/Swiggy): invoke both platform liability and restaurant liability
- Cite §3(1)(r) FSSA definition of "unsafe food" and §26 (responsibilities of food business operator)
- Reference FSSAI recall procedure — demand product batch recall if safety hazard""",
    "automobile": """\
CASE-TYPE STRATEGY — AUTOMOBILE DISPUTE:
- Lead with Motor Vehicles Act 1988 and BIS standards for vehicle safety
- If manufacturing defect: invoke CPA 2019 §§82-87 product liability (manufacturer + dealer joint liability)
- If warranty denied: cite warranty as contractual obligation + CPA 2019 §2(11) deficiency
- Reference SIAM (Society of Indian Automobile Manufacturers) code of conduct
- For service center disputes: cite BIS standards for auto servicing + unfair trade practices
- Demand vehicle inspection report under Motor Vehicles Act §56 (fitness certificate)
- If EV-related: cite BIS standards IS 17017 and FAME-II scheme compliance obligations
- File with company's nodal officer AND head office — most auto companies have structured grievance redressal""",
    "education": """\
CASE-TYPE STRATEGY — EDUCATION DISPUTE:
- Lead with CPA 2019 (education is a "service" per §2(42) read with Supreme Court precedent)
- If fee dispute: cite UGC/AICTE fee regulations and state fee regulatory committee orders
- If admission fraud: invoke IPC §420 (cheating) alongside consumer complaint — dual remedy
- For edtech refund: apply E-Commerce Rules 2020 + IT Act 2000 §79 intermediary obligations
- Reference UGC (Refund of Fees) Guidelines 2023 for higher education
- For coaching institutes: no specific regulator, but CPA 2019 fully applies — cite misleading advertisement §2(28)
- If placement guarantee broken: treat as unfair trade practice §2(47) — false promise of outcome
- File additionally with AICTE/UGC if institution is regulated""",
    "healthcare": """\
CASE-TYPE STRATEGY — HEALTHCARE/MEDICAL DISPUTE:
- Lead with Clinical Establishments Act 2010 (registration + minimum standards)
- If medical negligence: cite CPA 2019 §2(11) deficiency + Indian Medical Council (Professional Conduct) Regulations 2002
- Apply Bolam test (Indian adaptation): breach of reasonable standard of care per V. Kishan Rao v. Nikhil Super Speciality Hospital (2010) 5 SCC 513
- If excessive billing: invoke Clinical Establishments (Central Government) Rules 2012 on rate transparency
- Reference National Medical Commission Act 2019 and NMC guidelines on ethical practice
- Demand complete medical records under §1.3.2 of MCI Code of Ethics — patient has absolute right to records
- If drug reaction: invoke Drugs and Cosmetics Act 1940 + pharmacovigilance reporting to CDSCO
- File additionally with respective State Medical Council for professional misconduct""",
}


_SYSTEM_PROMPT = """\
You are a senior Indian consumer rights advocate with 25+ years of experience drafting \
formal Legal Notices under the Consumer Protection Act, 2019 and all applicable Indian \
statutes. You have argued hundreds of cases before the District Commission, State \
Commission, and NCDRC, and your notices are known for their devastating effectiveness.

ROLE: You are NOT writing a polite complaint letter. You are writing a formal legal \
document that will be served on the respondent company. Write like the most feared \
consumer lawyer in the country — one whose legal notices alone resolve 80%+ of disputes \
because companies know that ignoring them leads to expensive, embarrassing litigation.

═══════════════════════════════════════════════════════════════════════
LEGAL REASONING FRAMEWORK (follow this mental model BEFORE writing):
═══════════════════════════════════════════════════════════════════════

Before drafting each section, internally reason through:

1. FACT → LAW MAPPING: For every fact in the brief, identify which specific statutory \
   provision it violates. Never state a fact without its legal consequence.

2. EVIDENCE → CLAIM LINKING: For each piece of evidence, determine which specific claim \
   element it proves. Mention this link explicitly: "The [evidence] dated [date] \
   conclusively establishes [claim element] under [section]."

3. DEFENSE ANTICIPATION: For each claim, predict the company's 3 most likely defenses \
   and preemptively demolish each one with statutory override, precedent, or factual rebuttal.

4. PRESSURE CALIBRATION: Assess the dispute strength (strong evidence → aggressive demands; \
   weak evidence → emphasize procedural failures and regulatory pressure). Calibrate the \
   notice's assertiveness to the actual strength of the case.

5. QUANTUM REASONING: For damage claims, build the math — show the calculation: principal \
   amount + interest (rate × time) + mental agony (proportionate to facts) + litigation costs. \
   Never throw arbitrary numbers — every amount must be justified.

6. ESCALATION LOGIC: Sequence the escalation threats from most impactful to least, \
   ensuring each one targets a DIFFERENT vulnerability of the company (regulatory, \
   reputational, financial, compliance).

TONE & STYLE:
- Authoritative, precise, and assertive — not aggressive or threatening
- Every factual claim must be tied to a specific legal provision
- Cite exact statutory sections (not vague references)
- Anticipate and preemptively dismantle the company's likely T&C defenses
- Use the structure and language of real Indian legal notices
- Address the respondent in second person ("you", "your company")
- Maintain legal formality throughout
- Use ACTIVE voice, not passive. "You failed to deliver" not "It was not delivered"
- Use pointed, specific language. "Your company debited ₹12,499 on 15.03.2024" not "The amount was charged"
- Build logical chains: establish the fact → cite the violation → state the consequence → demand the remedy

PERSONALIZATION RULES (CRITICAL — do NOT produce generic/templated text):
- Reference the complainant's SPECIFIC facts, dates, amounts, order IDs, and names
- Weave the complainant's unique narrative into every section — do not use boilerplate
- When citing evidence, describe the ACTUAL documents and what they prove
- In the demand section, use the complainant's EXACT desired resolution and amounts
- Tailor statutory analysis to the SPECIFIC type of dispute (e-commerce, banking, telecom, etc.)
- If the company has a specific grievance officer, name them; if there's a ticket/ref number, cite it
- Make the chronology section read like a factual legal brief, not a generic timeline
- Do NOT use placeholder language like "the said product" — name the actual product/service
- Do NOT use generic phrases like "the complainant has suffered immense mental agony" without \
  connecting it to specific facts provided in the brief
- Every paragraph should contain at least one case-specific detail
- Name SPECIFIC dates (not "on the said date"), SPECIFIC amounts (not "the aforesaid sum"), \
  SPECIFIC products (not "the goods in question"), and SPECIFIC people (not "the concerned official")

ADVANCED DRAFTING TECHNIQUES:
- Build CAUSAL CHAINS: "Because [respondent's specific act/omission], the complainant suffered \
  [specific harm], which constitutes [specific legal violation] under [exact section], entitling \
  the complainant to [specific remedy]."
- Use the company's OWN WORDS against them: Quote their policy promises, website claims, \
  advertising slogans, or customer service representations — then show how their conduct \
  contradicts their own commitments.
- TEMPORAL PRESSURE: Calculate and state the exact number of days of delay/non-compliance. \
  "As of the date of this notice, {N} days have elapsed since [event] — far exceeding any \
  reasonable period and constituting continuing deficiency under §2(11) CPA 2019."
- PRECEDENT DEPLOYMENT: When citing case law, state the RATIO DECIDENDI — the principle \
  the court established — and show how it applies to the instant case on all fours.
- REGULATORY MULTIPLIER: Show how a single act of the respondent violates MULTIPLE statutes \
  simultaneously (e.g., CPA 2019 + E-Commerce Rules 2020 + IT Act 2000 + sector-specific regulation). \
  This amplifies the legal exposure.

MANDATORY SECTIONS (numbered, in this order):
1. Header: "LEGAL NOTICE" with date, addressee (company name, registered office, email), \
   respondent identification (CIN, LLPIN if available), sender details
2. Introduction: Assert consumer status under CPA 2019 §2(7), basis of notice
3. Statement of facts: Narrate the facts with lawyerly precision — every fact tied to a date and evidence
4. Chronology of events: Date-wise account establishing continuing cause of action, with \
   exact day-count between events showing progressive delay
5. Documentary evidence: List all evidence that will be produced, with what each piece proves
6. Legal basis: Cite EVERY applicable statutory provision with bare-act text verbatim. \
   Explain WHY each provision is attracted by the respondent's SPECIFIC conduct. Build the \
   fact→law→consequence chain for each provision.
7. Element-by-element claim analysis: Show which elements are satisfied per section, with \
   specific evidence mapped to each element
8. Preemptive rebuttal of T&C defenses (if any found): This is the KILLER section. \
   Quote the company's own T&C clause, then demolish it with statutory override + precedent. \
   For each defense: (a) quote their clause verbatim, (b) identify the statutory override, \
   (c) cite the precedent, (d) explain why the clause is void/unenforceable.
9. Arbitration clause rebuttal (if applicable): Cite Emaar MGF v. Aftab Singh (2019) 12 SCC 1; \
   also cite Perkins Eastman v. HSCC (2019) if applicable
10. Spirit of law and reasonableness
11. Limitation period assertion: State exact calculation showing the claim is within time
12. Jurisdiction determination: Show both pecuniary and territorial jurisdiction
13. Demand and relief sought: Item-by-item relief schedule with exact amounts, computation \
    methodology, interest calculation, and total quantum. Structure as a numbered list. \
    Include: (a) primary relief, (b) interest, (c) mental agony compensation (with factual basis), \
    (d) litigation costs.
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
- If the brief includes UPLOADED DOCUMENT EVIDENCE ANALYSIS, treat those extracted facts, amounts, \
  dates, and details as primary evidence. Reference them specifically in the facts, evidence, and \
  demand sections.
- If CUSTOMER PREFERENCES are provided, they MUST be respected (tone, compensation amount, interest rate)
- If DEMAND CALCULATION GUIDANCE is provided, use the exact computed figures in the demand section
- If EVIDENCE-TO-CLAIM MAP is provided, make every evidence→claim link explicit in the notice body
- If CASE-TYPE STRATEGY is provided, follow the sector-specific legal approach precisely
- The notice must be in ENGLISH only
- Output ONLY the notice text — no preamble, no markdown, no explanations
"""

# ── Refine/review prompt for second pass ─────────────────────────────

_REFINE_SYSTEM_PROMPT = """\
You are a senior supervising advocate reviewing a legal notice drafted by a junior. \
Your job is to STRENGTHEN, SHARPEN, and PERFECT the notice. You have 25+ years of \
consumer litigation experience in Indian courts.

REVIEW CRITERIA (check each one and fix if deficient):

1. SPECIFICITY CHECK: Every claim must reference specific dates, amounts, order IDs, \
   names. Replace ANY remaining generic language ("the said product", "the aforesaid amount", \
   "on the said date") with the ACTUAL specific details from the brief.

2. LEGAL PRECISION: Every statutory citation must include the EXACT section number and \
   match the bare-act text provided. Remove any hallucinated or inaccurate section references. \
   Verify each fact→law→consequence chain is logically sound.

3. EVIDENCE LINKAGE: Each claim must explicitly reference the supporting evidence. \
   If a claim has no linked evidence, either link available evidence or explicitly mark it \
   as a claim based on the complainant's statement (which is evidence under CPA 2019 §28).

4. DEMAND STRENGTH: The relief section must have precise calculations, not vague amounts. \
   Every demand should be itemized: principal + interest computation + mental agony + costs.

5. ESCALATION COMPLETENESS: Verify ALL escalation tactics from the brief are included. \
   Each one must name the specific authority, portal/mechanism, and legal basis.

6. ARGUMENTATIVE FORCE: Strengthen weak arguments. If a paragraph merely states a fact, \
   add the legal consequence. If a legal provision is cited without connecting it to the facts, \
   make the connection explicit.

7. DEFENSE DISMANTLING: Ensure every anticipated defense is preemptively addressed. \
   The T&C rebuttal must quote → statutory override → precedent for each clause.

8. TONE CONSISTENCY: The notice must maintain consistent tone throughout — no sudden \
   shifts from formal to colloquial or from assertive to passive.

9. CAUSAL CHAIN INTEGRITY: Check that every argument follows the pattern: \
   [Company's Act/Omission] → [Specific Harm to Consumer] → [Legal Violation under §X] → [Remedy/Consequence]

10. KILLER PARAGRAPH: Ensure there is at least one powerfully written paragraph that \
    would make any corporate legal counsel immediately flag this for settlement — typically \
    the paragraph that combines the strongest evidence with the most devastating legal consequence.

OUTPUT RULES:
- Return the COMPLETE refined notice — not just the changes.
- Preserve all 18 mandatory sections.
- Fix all deficiencies found above.
- If the draft is already excellent, make targeted improvements to maximize impact.
- Output ONLY the notice text — no review commentary, no preamble, no markdown.
"""


class NoticeDraftAgent:
    """Drafts a legal notice using Claude as the core writer.

    Uses a TWO-PASS pipeline for maximum intelligence:
    1. DRAFT pass: Full notice generation from the comprehensive brief
    2. REFINE pass: Senior advocate review that strengthens specificity,
       legal precision, evidence linkage, and argumentative force

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
        customer_controls: dict | None = None,
        document_analysis: dict | None = None,
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
            customer_controls=customer_controls,
            document_analysis=document_analysis,
        )

        # ── Adjust system prompt based on customer controls ──────────
        system_prompt = _SYSTEM_PROMPT
        cc = customer_controls or {}
        tone = cc.get("notice_tone")
        lang = cc.get("language", "English")

        tone_overrides = {
            "firm": "Authoritative, firm, and legally precise — conveys seriousness without hostility",
            "aggressive": "Aggressive, uncompromising, and confrontational — maximum legal pressure, treat as final warning before litigation",
            "diplomatic": "Diplomatic, professional, and solution-oriented — firm on rights but invites amicable resolution first",
        }
        if tone and tone in tone_overrides:
            system_prompt = system_prompt.replace(
                "Authoritative, precise, and assertive — not aggressive or threatening",
                tone_overrides[tone],
            )
        if lang and lang != "English":
            system_prompt = system_prompt.replace(
                "The notice must be in ENGLISH only",
                f"The notice must be in {lang}",
            )

        # ── PASS 1: Draft ────────────────────────────────────────────
        logger.info("Notice agent: drafting notice from brief")
        draft = await self.llm.complete_text(system_prompt, brief)
        return self._sanitize_notice(draft)

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
        claim_results: list[ClaimElementsResult] | None = None,
        limitation_result: LimitationResult | None = None,
        escalation_strategy: EscalationStrategy | None = None,
    ) -> list[str]:
        hints: list[str] = []
        issue = complaint.issue_summary.lower()
        desired = complaint.desired_resolution.lower()
        facts_combined = issue + " " + desired + " " + " ".join(complaint.timeline)

        # ── Relief-type strategy ─────────────────────────────────────
        if "refund" in facts_combined:
            hints.append(
                "REFUND STRATEGY: Lead demand with exact refund amount + interest computed from the date "
                "of transaction. Frame as restitutio in integrum (restoration to original position). "
                "Add that failure to refund within the cure period constitutes continuing deficiency "
                "attracting additional interest under §2(11) CPA 2019."
            )
        if "replacement" in facts_combined or "replace" in facts_combined:
            hints.append(
                "REPLACEMENT STRATEGY: Demand replacement within cure period as PRIMARY relief, "
                "with AUTOMATIC escalation to full refund + compensation if replacement not provided. "
                "Cite §39(1)(b) CPA 2019 (replacement of goods) alongside §39(1)(a) (refund as fallback)."
            )
        if "repair" in facts_combined or "service" in facts_combined:
            hints.append(
                "SERVICE/REPAIR STRATEGY: Frame as deficiency in service under §2(11) CPA 2019. "
                "Demand specific performance (complete the repair/service) within cure period, "
                "with monetary compensation for the period of deprivation."
            )

        # ── Evidence strength calibration ────────────────────────────
        if evidence_score:
            score = evidence_score.overall_score
            if score >= 8:
                hints.append(
                    f"STRONG EVIDENCE (score: {score}/10): Take an aggressive litigation posture. "
                    "Emphasize that the complainant possesses overwhelming documentary evidence "
                    "that will be produced before the Consumer Commission. "
                    "Challenge the respondent to contradict ANY of the documented facts."
                )
            elif score >= 5:
                hints.append(
                    f"MODERATE EVIDENCE (score: {score}/10): Balance documentary evidence with "
                    "statutory presumptions favoring consumers. Invoke §94 CPA 2019 (burden of proof "
                    "on respondent to show they did NOT commit unfair trade practice). "
                    "Emphasize that even the respondent's own records will corroborate the complaint."
                )
            else:
                hints.append(
                    f"LIMITED EVIDENCE (score: {score}/10): Lead with regulatory pressure tactics rather "
                    "than pure litigation threat. Emphasize: (a) respondent's obligation to maintain records "
                    "under §2(47)(ix), (b) demand document preservation by respondent, (c) complainant's "
                    "statement itself is evidence under §28 CPA 2019 affidavit procedure."
                )

            if evidence_score.contradictions:
                hints.append(
                    "CONTRADICTIONS DETECTED: Avoid overclaiming disputed facts. Build argument on "
                    "the STRONGEST, most consistent documentary evidence points only. Acknowledge "
                    "minor discrepancies upfront to maintain credibility and prevent respondent from "
                    "using them to discredit the entire claim."
                )
            if evidence_score.gaps:
                gap_count = len(evidence_score.gaps)
                hints.append(
                    f"EVIDENCE GAPS ({gap_count} found): Add an evidence preservation demand requiring "
                    "respondent to retain ALL records (call logs, chat transcripts, CCTV footage, "
                    "delivery tracking, internal ticket history) pending adjudication. Frame the "
                    "respondent's failure to produce these records as adverse inference under §28 CPA 2019."
                )

        elif not complaint.evidence:
            hints.append(
                "NO EVIDENCE LISTED: Insert a STRONG evidence preservation demand. Cite Information "
                "Technology Act 2000 §67C (records retention obligation) and CPA 2019 §28 (affidavit "
                "procedure — complainant's sworn statement IS evidence). Frame respondent's records "
                "as the BEST evidence and demand their production."
            )

        # ── Timeline strength ────────────────────────────────────────
        timeline_count = len(complaint.timeline)
        if timeline_count >= 5:
            hints.append(
                f"RICH TIMELINE ({timeline_count} events): Build a devastating day-by-day chronology "
                "that shows a PATTERN of neglect and delay. Calculate exact days between each event. "
                "Highlight the longest gap as evidence of willful non-compliance."
            )
        elif timeline_count >= 2:
            hints.append(
                "MODERATE TIMELINE: Anchor the chronology on concrete dates. Calculate the total "
                "elapsed days from first complaint to present. Frame this duration as unreasonable "
                "and establishing continuing cause of action."
            )
        elif timeline_count < 2:
            hints.append(
                "SPARSE TIMELINE: Strengthen chronology by anchoring on the transaction date and "
                "current date. Calculate total days of inaction. Use language like 'despite the "
                "efflux of [N] days, the respondent has failed to address...'"
            )

        # ── T&C defense preparation ────────────────────────────────
        if tc_counter_result and tc_counter_result.counters:
            counter_count = len(tc_counter_result.counters)
            hints.append(
                f"T&C DEFENSES IDENTIFIED ({counter_count}): In rebuttal section, use a systematic "
                "three-step demolition for EACH clause: (1) Quote verbatim, (2) Identify statutory "
                "override provision, (3) Cite precedent. End with: 'The aforesaid clauses, being "
                "contrary to the provisions of the CPA 2019, are void ab initio and unenforceable.'"
            )

        # ── Arbitration handling ─────────────────────────────────────
        if arbitration_result and arbitration_result.clauses_found:
            hints.append(
                "ARBITRATION CLAUSE DETECTED: Deploy the Emaar MGF v. Aftab Singh (2019) 12 SCC 1 "
                "ratio plus Perkins Eastman v. HSCC (2019) 20 SCC 760. Key argument: consumer "
                "disputes are non-arbitrable when they involve unfair contract terms. Keep rebuttal "
                "concise but definitive — place IMMEDIATELY after T&C rebuttal to prevent forum-shopping."
            )

        # ── Claim analysis integration ───────────────────────────────
        if claim_results:
            all_pass = all(cr.overall_pass for cr in claim_results)
            partial_count = sum(1 for cr in claim_results if not cr.overall_pass)
            if all_pass:
                hints.append(
                    "ALL CLAIM ELEMENTS SATISFIED: Take a confident, assertive posture throughout. "
                    "State that the complainant has made out a PRIMA FACIE case on ALL counts and "
                    "the respondent's liability is beyond reasonable doubt."
                )
            elif partial_count > 0:
                hints.append(
                    f"PARTIAL CLAIMS ({partial_count} with gaps): Lead with the STRONGEST claim "
                    "elements first. For partial claims, emphasize the satisfied elements and frame "
                    "unsatisfied ones as remediable through document production at hearing stage. "
                    "Use reverse burden of proof under CPA 2019 §94 for unfair trade practice claims."
                )

        # ── Limitation awareness ─────────────────────────────────────
        if limitation_result:
            warning = limitation_result.warning.lower()
            if "expiring" in warning or "urgent" in warning:
                hints.append(
                    "TIME-SENSITIVE CLAIM: Emphasize urgency. State the limitation period explicitly "
                    "and note that the notice is being served to preserve the right to file before the "
                    "Consumer Commission. Add: 'The complainant reserves the right to file the complaint "
                    "forthwith without awaiting the expiry of the cure period if necessitated by limitation.'"
                )

        # ── Emotional/harassment component ──────────────────────────
        if "mental agony" in facts_combined or "harassment" in facts_combined or "stress" in facts_combined:
            hints.append(
                "MENTAL AGONY CLAIM: State compensation as PROPORTIONATE and evidence-linked. "
                "Connect it to specific incidents of harassment (e.g., repeated calls, runaround, "
                "emotional distress from financial loss). Cite Spring Meadows Hospital v. Harjol "
                "Ahluwalia (1998) 4 SCC 39 for consumer's right to compensation for mental agony."
            )

        # ── Escalation power ────────────────────────────────────────
        if escalation_strategy and escalation_strategy.tactics:
            tactic_count = len(escalation_strategy.tactics)
            hints.append(
                f"ESCALATION ARSENAL ({tactic_count} tactics): Weave ALL tactics into the notice. "
                "Structure them as a MULTI-FRONT assault: regulatory (sector regulator), "
                "governmental (CPGRAMS/PMO), consumer forum (commission filing), and reputational "
                "(social media/review platforms). The combined effect should create overwhelming "
                "pressure from multiple simultaneous directions."
            )

        return hints

    @staticmethod
    def _detect_case_type(complaint: ComplaintInput, company: CompanyProfile) -> str | None:
        """Detect the dispute sector to enable case-type specialization."""
        text = (
            (complaint.issue_summary + " " + complaint.desired_resolution + " "
             + (company.brand_name or "") + " " + (company.domain or ""))
            .lower()
        )
        best_match: str | None = None
        best_count = 0
        for case_type, keywords in _CASE_TYPE_SIGNALS.items():
            count = sum(1 for kw in keywords if kw in text)
            if count > best_count:
                best_count = count
                best_match = case_type
        return best_match if best_count >= 2 else None

    @staticmethod
    def _compute_demand_guidance(
        complaint: ComplaintInput,
        cure_days: int,
        customer_controls: dict | None = None,
        evidence_score: EvidenceScore | None = None,
    ) -> list[str]:
        """Compute intelligent demand guidance with actual calculations."""
        guidance: list[str] = []
        cc = customer_controls or {}
        today = datetime.utcnow().date()

        # Try to extract a principal amount from the complaint
        amount_match = re.search(
            r'(?:rs\.?|₹|inr)\s*([\d,]+(?:\.\d{1,2})?)',
            complaint.issue_summary + " " + complaint.desired_resolution,
            re.I,
        )
        principal = None
        if amount_match:
            try:
                principal = float(amount_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # Customer-specified compensation overrides
        comp_amount = cc.get("compensation_amount")
        interest_rate = cc.get("interest_rate_percent", 18)  # default 18% p.a.

        if principal:
            guidance.append(f"PRINCIPAL AMOUNT IDENTIFIED: ₹{principal:,.2f}")

            # Interest calculation
            # Try to find a transaction date in the timeline
            date_match = None
            for event in complaint.timeline:
                dm = re.search(r'(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})', event)
                if dm:
                    date_match = dm
                    break

            if date_match:
                try:
                    d, m, y = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
                    if y < 100:
                        y += 2000
                    from datetime import date as date_cls
                    txn_date = date_cls(y, m, d)
                    days_elapsed = (today - txn_date).days
                    if days_elapsed > 0:
                        interest_amount = principal * (interest_rate / 100) * (days_elapsed / 365)
                        guidance.append(
                            f"INTEREST CALCULATION: ₹{principal:,.2f} × {interest_rate}% p.a. × "
                            f"{days_elapsed} days = ₹{interest_amount:,.2f}"
                        )
                        guidance.append(f"Days elapsed since transaction: {days_elapsed}")
                except (ValueError, OverflowError):
                    guidance.append(
                        f"INTEREST RATE: Apply {interest_rate}% per annum from the date of transaction"
                    )
            else:
                guidance.append(
                    f"INTEREST RATE: Apply {interest_rate}% per annum from the date of transaction"
                )

            # Mental agony suggestion based on evidence strength and principal
            if evidence_score and evidence_score.overall_score >= 7:
                mental_agony = max(10000, round(principal * 0.3, -3))  # 30% of principal, min ₹10,000
                guidance.append(
                    f"SUGGESTED MENTAL AGONY: ₹{mental_agony:,.0f} (30% of principal — "
                    "strong evidence supports higher compensation)"
                )
            elif evidence_score and evidence_score.overall_score >= 4:
                mental_agony = max(5000, round(principal * 0.15, -3))  # 15% of principal, min ₹5,000
                guidance.append(
                    f"SUGGESTED MENTAL AGONY: ₹{mental_agony:,.0f} (15% of principal — "
                    "moderate evidence, proportionate claim)"
                )
            else:
                mental_agony = 5000
                guidance.append(
                    f"SUGGESTED MENTAL AGONY: ₹{mental_agony:,.0f} (minimum reasonable — "
                    "limited evidence, keep claim proportionate)"
                )

            # Litigation cost estimate
            litigation_cost = max(5000, round(principal * 0.1, -3))
            guidance.append(f"LITIGATION COSTS: ₹{litigation_cost:,.0f} (estimated filing + advocate fees)")

            # Total quantum
            if comp_amount:
                guidance.append(f"CUSTOMER-SPECIFIED COMPENSATION: ₹{comp_amount:,} (use this as the total demand)")
            else:
                total = principal + mental_agony + litigation_cost
                guidance.append(f"TOTAL MINIMUM DEMAND: ₹{total:,.0f} (principal + mental agony + litigation costs)")
                guidance.append("NOTE: Interest is ADDITIONAL and should be computed up to the date of payment")

        elif comp_amount:
            guidance.append(f"CUSTOMER-SPECIFIED COMPENSATION: ₹{comp_amount:,} (use this as the total demand)")

        guidance.append(f"CURE PERIOD: {cure_days} days from receipt of this notice")

        return guidance

    @staticmethod
    def _cross_reference_evidence(
        complaint: ComplaintInput,
        claim_results: list[ClaimElementsResult],
        evidence_score: EvidenceScore | None,
        document_analysis: dict | None,
    ) -> list[str]:
        """Map evidence items to the specific legal claims they support."""
        mappings: list[str] = []

        evidence_items = list(complaint.evidence or [])
        # Add uploaded document evidence
        if document_analysis and document_analysis.get("documents"):
            for doc in document_analysis["documents"]:
                evidence_items.append(f"Uploaded: {doc.get('filename', 'document')} — {doc.get('summary', 'analyzed')}")

        if not evidence_items or not claim_results:
            return mappings

        for i, item in enumerate(evidence_items, 1):
            item_lower = item.lower()
            matching_claims = []
            for cr in claim_results:
                for check in cr.checks:
                    # Find semantic overlap between evidence item and claim element
                    element_words = set(check.element.lower().split())
                    item_words = set(item_lower.split())
                    overlap = element_words & item_words
                    # Also check for amount/date/transaction references
                    has_amount = bool(re.search(r'₹|rs|amount|price|cost|fee|charge', item_lower))
                    has_date = bool(re.search(r'\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec', item_lower))

                    if (len(overlap) >= 2 or
                        (has_amount and ("payment" in check.element.lower() or "consideration" in check.element.lower())) or
                        (has_date and "timeline" in check.element.lower())):
                        matching_claims.append(f"{cr.section.act} {cr.section.section} — {check.element}")

            if matching_claims:
                mappings.append(f"Evidence {i}: \"{item[:100]}\"")
                for claim in matching_claims[:3]:
                    mappings.append(f"  → Supports: {claim}")

        return mappings

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
        customer_controls: dict | None = None,
        document_analysis: dict | None = None,
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

        # ── Strategic drafting hints (ENHANCED) ────────────────────
        strategy_hints = self._strategy_hints(
            complaint=complaint,
            evidence_score=evidence_score,
            arbitration_result=arbitration_result,
            tc_counter_result=tc_counter_result,
            claim_results=claim_results,
            limitation_result=limitation_result,
            escalation_strategy=escalation_strategy,
        )
        if strategy_hints:
            b.append("\n## STRATEGIC DRAFTING HINTS (follow ALL of these)")
            for hint in strategy_hints:
                b.append(f"- {hint}")

        # ── Case-type specialization ─────────────────────────────────
        case_type = self._detect_case_type(complaint, company)
        if case_type and case_type in _CASE_TYPE_STRATEGY:
            b.append(f"\n## {_CASE_TYPE_STRATEGY[case_type]}")

        # ── Intelligent demand calculation ───────────────────────────
        demand_guidance = self._compute_demand_guidance(
            complaint=complaint,
            cure_days=cure_days,
            customer_controls=customer_controls,
            evidence_score=evidence_score,
        )
        if demand_guidance:
            b.append("\n## DEMAND CALCULATION GUIDANCE (use these exact figures)")
            for line in demand_guidance:
                b.append(f"- {line}")

        # ── Evidence-to-claim cross-reference ────────────────────────
        cross_refs = self._cross_reference_evidence(
            complaint=complaint,
            claim_results=claim_results,
            evidence_score=evidence_score,
            document_analysis=document_analysis,
        )
        if cross_refs:
            b.append("\n## EVIDENCE-TO-CLAIM MAP (make these links EXPLICIT in the notice)")
            for ref in cross_refs:
                b.append(ref)

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

        # ── Customer preferences (override defaults) ────────────────
        cc = customer_controls or {}
        has_prefs = any(cc.get(k) for k in ("notice_tone", "compensation_amount", "interest_rate_percent", "language"))
        if has_prefs:
            b.append(f"\n## CUSTOMER PREFERENCES (MANDATORY — respect these)")
            if cc.get("notice_tone"):
                tone_map = {
                    "firm": "firm, authoritative, legally precise",
                    "aggressive": "aggressive, confrontational, maximum legal pressure",
                    "diplomatic": "diplomatic, professional, solution-oriented while firm on rights",
                }
                b.append(f"Requested tone: {tone_map.get(cc['notice_tone'], cc['notice_tone'])}")
            if cc.get("compensation_amount"):
                b.append(f"Demanded compensation amount: ₹{cc['compensation_amount']:,} (use this EXACT amount in the demand section)")
            if cc.get("interest_rate_percent"):
                b.append(f"Interest rate on refund/dues: {cc['interest_rate_percent']}% per annum (include this in the demand)")
            if cc.get("language") and cc["language"] != "English":
                b.append(f"Output language: {cc['language']}")

        # ── Document evidence analysis (from uploaded files) ─────────
        if document_analysis and document_analysis.get("documents"):
            b.append(f"\n## UPLOADED DOCUMENT EVIDENCE ANALYSIS")
            b.append("The following documents were uploaded and analyzed by AI. Use their content to strengthen the notice.")
            b.append("IMPORTANT: Reference specific facts, amounts, dates, and details extracted from these documents IN the notice text.")
            for doc in document_analysis["documents"]:
                b.append(f"\n### Document: {doc.get('filename', 'Unknown')}")
                b.append(f"Type: {doc.get('document_type', 'Unknown')}")
                b.append(f"Relevance: {doc.get('relevance', 'Unknown')}")
                if doc.get("key_facts"):
                    b.append("Key facts extracted:")
                    for fact in doc["key_facts"]:
                        b.append(f"  - {fact}")
                if doc.get("amounts"):
                    b.append("Amounts/values found:")
                    for amt in doc["amounts"]:
                        b.append(f"  - {amt}")
                if doc.get("dates"):
                    b.append("Dates found:")
                    for d in doc["dates"]:
                        b.append(f"  - {d}")
                if doc.get("summary"):
                    b.append(f"Summary: {doc['summary']}")

        return "\n".join(b)
