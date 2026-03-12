"""Escalation pressure strategy agent.

Uses Claude to determine applicable non-litigation pressure tactics
tailored to the specific dispute, company, and industry. Falls back
to keyword-based industry detection if LLM unavailable.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from legaltech.schemas import ComplaintInput, CompanyProfile, PolicyEvidence

logger = logging.getLogger(__name__)


@dataclass
class PressureTactic:
    tactic: str              # short label
    action: str              # what will be done
    target_authority: str    # who it's directed at
    legal_basis: str         # statute / rule enabling this
    impact_description: str  # why company should care
    applies: bool = True


@dataclass
class EscalationStrategy:
    tactics: list[PressureTactic] = field(default_factory=list)
    severity_level: str = "standard"  # "standard", "elevated", "maximum"
    summary: str = ""


# ── Industry detection keywords ──────────────────────────────────────

_INDUSTRY_SIGNALS: dict[str, tuple[str, ...]] = {
    "banking_finance": ("bank", "loan", "emi", "credit card", "debit card", "upi", "wallet",
                        "nbfc", "fintech", "insurance", "mutual fund", "investment",
                        "neft", "rtgs", "imps", "aadhaar pay", "razorpay", "paytm", "phonepe"),
    "ecommerce": ("order", "delivery", "refund", "product", "amazon", "flipkart", "myntra",
                  "meesho", "snapdeal", "e-commerce", "ecommerce", "online shopping",
                  "cart", "cod", "cash on delivery", "marketplace"),
    "telecom": ("mobile", "sim", "recharge", "broadband", "jio", "airtel", "vodafone", "vi",
                "bsnl", "telecom", "network", "data plan", "porting", "trai"),
    "airline_travel": ("flight", "airline", "ticket", "booking", "cancell", "airport",
                       "boarding", "refund", "indigo", "air india", "spicejet", "vistara",
                       "dgca", "travel", "hotel", "makemytrip", "goibibo"),
    "real_estate": ("flat", "apartment", "builder", "possession", "rera", "real estate",
                    "construction", "housing", "property", "registry", "developer"),
    "insurance": ("policy", "claim", "premium", "insurance", "irdai", "life insurance",
                  "health insurance", "motor insurance", "mediclaim", "cashless"),
    "food_fmcg": ("food", "fssai", "expired", "contaminated", "restaurant", "zomato",
                  "swiggy", "grocery", "bigbasket", "blinkit", "instamart"),
    "automobile": ("car", "vehicle", "service center", "dealer", "warranty", "automobile",
                   "ev", "bike", "scooter"),
    "education": ("university", "college", "coaching", "edtech", "course", "admission",
                  "fee", "byju", "unacademy", "upgrad"),
    "healthcare": ("hospital", "doctor", "treatment", "medical", "clinic", "pharmacy",
                   "lab", "diagnosis", "surgery"),
}

# ── Sector-specific regulators ───────────────────────────────────────

_SECTOR_REGULATORS: dict[str, list[tuple[str, str, str]]] = {
    # (regulator name, complaint mechanism, legal basis)
    "banking_finance": [
        ("RBI Ombudsman", "File complaint on cms.rbi.org.in under Integrated Ombudsman Scheme 2021",
         "RBI Integrated Ombudsman Scheme 2021; Banking Regulation Act 1949"),
        ("Reserve Bank of India", "Flag non-compliance with RBI Master Directions on customer service",
         "RBI Charter of Customer Rights 2014"),
    ],
    "ecommerce": [
        ("Central Consumer Protection Authority (CCPA)",
         "File complaint for unfair trade practice / misleading advertisement",
         "CPA 2019 §§10-27 (CCPA powers including product recall, penalty up to ₹50 lakh)"),
        ("Department of Consumer Affairs",
         "Escalate via INGRAM portal (ingram.gov.in) or NCH (1800-11-4000)",
         "Consumer Protection Act, 2019"),
    ],
    "telecom": [
        ("TRAI / Telecom Ombudsman",
         "File complaint with TRAI via trai.gov.in and Telecom Consumers Complaint Monitoring System",
         "TRAI Act 1997; Telecom Consumer Grievance Redressal Regulations 2012"),
    ],
    "airline_travel": [
        ("Director General of Civil Aviation (DGCA)",
         "File complaint on AirSewa portal (airsewa.gov.in)",
         "Aircraft Rules 1937 Rule 135C; DGCA CAR Section 3 Series M Part IV"),
    ],
    "real_estate": [
        ("RERA Authority (state-specific)",
         "File complaint on state RERA portal for delayed possession / builder default",
         "Real Estate (Regulation and Development) Act, 2016 §31"),
    ],
    "insurance": [
        ("IRDAI / Insurance Ombudsman",
         "File complaint via igms.irda.gov.in; escalate to Insurance Ombudsman",
         "IRDAI (Protection of Policyholders' Interest) Regulations 2017"),
    ],
    "food_fmcg": [
        ("FSSAI / Food Safety Commissioner",
         "Report unsafe/expired food on fssai.gov.in; state Food Safety Officer complaint",
         "Food Safety and Standards Act, 2006 §§42-65"),
    ],
    "automobile": [
        ("Society of Indian Automobile Manufacturers (SIAM) / CCPA",
         "Report defective vehicle; CCPA can order product recall under CPA 2019 §18(2)(l)",
         "CPA 2019 §§18, 84 (product liability for manufacturer)"),
    ],
    "education": [
        ("UGC / AICTE / relevant regulatory body",
         "Flag non-compliance with UGC/AICTE norms for fee refund, admission, or curriculum issues",
         "UGC Regulations; AICTE Approval Process Handbook"),
    ],
    "healthcare": [
        ("National/State Medical Commission",
         "File complaint for medical negligence or overcharging",
         "National Medical Commission Act 2019; Clinical Establishments Act 2010"),
    ],
}


_ESCALATION_SYSTEM_PROMPT = """\
You are a senior Indian consumer rights strategist. Given a consumer complaint, \
company profile, and dispute context, determine the most effective non-litigation \
pressure tactics to include in the legal notice.

Your goal: make the legal notice so credible and multi-pronged that the company's \
legal team concludes that resolution is cheaper than fighting.

For each tactic, provide:
1. Tactic name (short label)
2. Specific action the consumer will take
3. Target authority / body
4. Legal basis (statute, regulation, or scheme)
5. Impact description (why the company should care)

MANDATORY TACTICS (include for ALL disputes):
- Director personal liability (CPA 2019 §89)
- CCPA complaint (CPA 2019 §18, penalty up to ₹50 lakh)
- Government portal escalation (NCH, INGRAM, CPGRAMS)
- Public review / social media (Article 19(1)(a))
- Criminal remedies reservation (BNS 2023 §318-319)

SECTOR-SPECIFIC (include if applicable):
- Banking/finance: RBI Ombudsman, RBI Charter of Customer Rights
- E-commerce: E-Commerce Rules 2020 violation, CCPA recall powers
- Telecom: TRAI, Telecom Ombudsman
- Airlines/travel: DGCA, AirSewa portal
- Real estate: state RERA Authority
- Insurance: IRDAI, Insurance Ombudsman
- Food/FMCG: FSSAI, Food Safety Commissioner
- Healthcare: National Medical Commission
- Education: UGC/AICTE
- Data/privacy: Data Protection Board (DPDP Act 2023, penalty up to ₹250 crore)
- Refund/payment: GST authority flag (CGST Act 2017 §34)
- Listed companies: SEBI / LODR disclosure

Also determine severity level: standard, elevated, or maximum.
Include a multi-stakeholder CC strategy listing all entities to copy on the notice.

Return JSON:
{
  "tactics": [
    {
      "tactic": "short label",
      "action": "detailed action description",
      "target_authority": "who it targets",
      "legal_basis": "statute/regulation reference",
      "impact_description": "why company should care"
    }
  ],
  "severity_level": "standard|elevated|maximum",
  "summary": "overall strategy summary",
  "detected_industries": ["list of relevant industry sectors"]
}

Return ONLY the JSON.
"""


class EscalationStrategyAgent:
    """Determines applicable non-litigation pressure tactics."""

    def __init__(self, llm=None) -> None:
        self.llm = llm

    async def run(
        self,
        complaint: ComplaintInput,
        company: CompanyProfile,
        policies: list[PolicyEvidence],
        contacts_found: int,
        respondent_identity_found: bool,
        evidence_count: int,
        claim_amount_hint: str | None = None,
    ) -> EscalationStrategy:
        if self.llm:
            try:
                return await self._agentic_run(
                    complaint, company, policies, contacts_found,
                    respondent_identity_found, evidence_count, claim_amount_hint,
                )
            except Exception as exc:
                logger.warning("LLM escalation strategy failed, using fallback: %s", exc)
        return self._deterministic_run(
            complaint, company, policies, contacts_found,
            respondent_identity_found, evidence_count, claim_amount_hint,
        )

    async def _agentic_run(
        self,
        complaint: ComplaintInput,
        company: CompanyProfile,
        policies: list[PolicyEvidence],
        contacts_found: int,
        respondent_identity_found: bool,
        evidence_count: int,
        claim_amount_hint: str | None,
    ) -> EscalationStrategy:
        company_label = company.legal_name or company.brand_name or "the company"
        user_prompt = (
            f"## Complaint Summary\n{complaint.issue_summary}\n\n"
            f"## Desired Resolution\n{complaint.desired_resolution}\n\n"
            f"## Company\nName: {company_label}\nDomain: {company.domain or 'unknown'}\n\n"
            f"## Context\n"
            f"- Contacts found: {contacts_found}\n"
            f"- Respondent identity verified: {respondent_identity_found}\n"
            f"- Evidence items: {evidence_count}\n"
            f"- Claim amount hint: {claim_amount_hint or 'not specified'}\n"
            f"- Timeline entries: {len(complaint.timeline)}\n"
            f"- Policies scraped: {len(policies)}\n"
        )
        data = await self.llm.complete_json(_ESCALATION_SYSTEM_PROMPT, user_prompt)

        tactics = [
            PressureTactic(
                tactic=t["tactic"],
                action=t["action"],
                target_authority=t.get("target_authority", ""),
                legal_basis=t.get("legal_basis", ""),
                impact_description=t.get("impact_description", ""),
            )
            for t in data.get("tactics", [])
        ]
        return EscalationStrategy(
            tactics=tactics,
            severity_level=data.get("severity_level", "standard"),
            summary=data.get("summary", ""),
        )

    def _deterministic_run(
        self,
        complaint: ComplaintInput,
        company: CompanyProfile,
        policies: list[PolicyEvidence],
        contacts_found: int,
        respondent_identity_found: bool,
        evidence_count: int,
        claim_amount_hint: str | None = None,
    ) -> EscalationStrategy:
        corpus = " ".join([
            complaint.issue_summary,
            complaint.desired_resolution,
            " ".join(complaint.timeline),
            " ".join(complaint.evidence),
            company.brand_name or "",
            company.legal_name or "",
            company.domain or "",
        ]).lower()

        # Detect industries
        detected_industries = self._detect_industries(corpus)
        tactics: list[PressureTactic] = []

        # ── 1. Universal tactics (apply to ALL disputes) ─────────────

        # Director personal liability
        tactics.append(PressureTactic(
            tactic="Director Personal Liability",
            action=(
                "Hold the Managing Director / Directors personally liable for the "
                "deficiency under CPA 2019 §89, which provides that where an offence "
                "is committed by a company, every person who was in charge of the company "
                "at the time shall be deemed guilty"
            ),
            target_authority="Named directors of the company",
            legal_basis="Consumer Protection Act, 2019 §89 (offences by companies)",
            impact_description=(
                "Directors face personal prosecution and reputational risk; this is a "
                "powerful motivator for quick resolution as it pierces the corporate veil"
            ),
        ))

        # CCPA complaint — unfair trade practice
        tactics.append(PressureTactic(
            tactic="CCPA Complaint",
            action=(
                "File complaint with the Central Consumer Protection Authority (CCPA) "
                "under CPA 2019 §18 for unfair trade practice and/or misleading conduct, "
                "which empowers CCPA to impose penalty up to ₹10 lakh (first offence) / "
                "₹50 lakh (subsequent) and order product recall"
            ),
            target_authority="Central Consumer Protection Authority (CCPA)",
            legal_basis="CPA 2019 §§10-27, Rules 2020",
            impact_description=(
                "CCPA can impose monetary penalties, issue directions to discontinue unfair "
                "practices, and order product recall — affects entire business, not just this complaint"
            ),
        ))

        # National Consumer Helpline + INGRAM
        tactics.append(PressureTactic(
            tactic="Government Portal Escalation",
            action=(
                "Register complaint on National Consumer Helpline (NCH, 1800-11-4000), "
                "INGRAM portal (ingram.gov.in), and CPGRAMS (pgportal.gov.in) for "
                "central/state government intervention"
            ),
            target_authority="Ministry of Consumer Affairs / NCH / CPGRAMS",
            legal_basis="Consumer Protection Act, 2019; Government e-Governance initiatives",
            impact_description=(
                "Government portal complaints create official records that affect company's "
                "compliance ratings; NCH convergence with companies forces response within 45 days; "
                "CPGRAMS complaints are tracked by PMO"
            ),
        ))

        # Social media & consumer forums reputation pressure
        tactics.append(PressureTactic(
            tactic="Public Review & Social Media Escalation",
            action=(
                "Document this experience on ConsumerComplaints.in, MouthShut.com, "
                "Google Business Reviews, Trustpilot, and social media platforms (X/Twitter, "
                "LinkedIn) with factual account and evidence, tagging the company's official handles "
                "and relevant consumer rights organizations"
            ),
            target_authority="Public domain / social media",
            legal_basis="Right to information and free speech under Article 19(1)(a) of the Constitution",
            impact_description=(
                "Public complaints create SEO-indexed records that appear in search results, "
                "damaging brand reputation and affecting customer acquisition; companies with "
                "high complaint volumes face regulatory scrutiny"
            ),
        ))

        # MCA / ROC non-compliance
        if not respondent_identity_found:
            tactics.append(PressureTactic(
                tactic="MCA/ROC Non-Compliance Flag",
                action=(
                    "Report non-disclosure of company identity information (CIN, registered office, "
                    "grievance officer) to Registrar of Companies (ROC) as violation of "
                    "Companies Act 2013 §12 (registered office display) and E-Commerce Rules 2020"
                ),
                target_authority="Registrar of Companies (ROC) / Ministry of Corporate Affairs",
                legal_basis="Companies Act 2013 §§12, 92; E-Commerce Rules 2020 Rule 4",
                impact_description=(
                    "ROC non-compliance can trigger show-cause notices, penalties under §450 "
                    "(₹10,000/day), and adverse entries in the company's MCA21 record"
                ),
            ))

        # E-Commerce Rules specific compliance
        if "ecommerce" in detected_industries or any(k in corpus for k in ("online", "website", "app", "platform")):
            tactics.append(PressureTactic(
                tactic="E-Commerce Rules Violation Report",
                action=(
                    "Report specific violations of Consumer Protection (E-Commerce) Rules, 2020: "
                    "Rule 4 (mandatory information display), Rule 5 (marketplace duties), "
                    "Rule 6 (inventory e-commerce duties) including failure to provide "
                    "grievance redressal within stipulated 48-hour acknowledgment "
                    "and 1-month resolution timeline"
                ),
                target_authority="Department of Consumer Affairs / CCPA",
                legal_basis="Consumer Protection (E-Commerce) Rules, 2020, Rules 4-6",
                impact_description=(
                    "E-Commerce Rules violations can result in CCPA directions to "
                    "discontinue business practices and monetary penalties"
                ),
            ))

        # Data Protection complaint
        if any(k in corpus for k in ("data", "personal", "account", "privacy", "password", "otp", "aadhaar", "pan")):
            tactics.append(PressureTactic(
                tactic="Data Protection Board Complaint",
                action=(
                    "File complaint with the Data Protection Board of India under "
                    "Digital Personal Data Protection Act, 2023 §§8-13 for failure to "
                    "protect personal data, unauthorized processing, or failure to erase "
                    "data upon request"
                ),
                target_authority="Data Protection Board of India",
                legal_basis="DPDP Act 2023 §§8, 13, 33 (penalty up to ₹250 crore)",
                impact_description=(
                    "DPDP Act penalties range from ₹50 crore to ₹250 crore per breach; "
                    "even a complaint triggers compliance audit obligations"
                ),
            ))

        # GST implications for delayed refunds
        if any(k in corpus for k in ("refund", "money", "payment", "charged", "debit")):
            tactics.append(PressureTactic(
                tactic="GST Refund & Tax Authority Flag",
                action=(
                    "Flag to GST authorities that the company has collected GST on a "
                    "transaction for which goods/services were not delivered or for which "
                    "refund is due — creating potential GST reversal obligation under "
                    "CGST Act 2017 §34 (credit/debit notes for deficient supply)"
                ),
                target_authority="GST Authority / Commissioner",
                legal_basis="CGST Act 2017 §34 (credit notes), §122 (offences and penalties)",
                impact_description=(
                    "Companies must issue credit notes and reverse GST for deficient supplies; "
                    "failure to do so attracts penalties under §122 and can trigger GST audit"
                ),
            ))

        # ── 2. Sector-specific tactics ───────────────────────────────

        for industry in detected_industries:
            regulators = _SECTOR_REGULATORS.get(industry, [])
            for reg_name, reg_action, reg_basis in regulators:
                tactics.append(PressureTactic(
                    tactic=f"Sector Regulator: {reg_name}",
                    action=reg_action,
                    target_authority=reg_name,
                    legal_basis=reg_basis,
                    impact_description=(
                        f"Regulatory complaint to {reg_name} creates compliance obligation; "
                        f"repeated complaints affect the company's regulatory standing "
                        f"and can trigger formal investigation"
                    ),
                ))

        # ── 3. Elevated: Listed company specific ─────────────────────

        listed_signals = ("nse", "bse", "listed", "share", "stock", "ipo", "sebi")
        if any(k in corpus for k in listed_signals):
            tactics.append(PressureTactic(
                tactic="SEBI / Stock Exchange Disclosure",
                action=(
                    "Notify SEBI and relevant stock exchange that the company's consumer "
                    "complaint handling practices may constitute material non-disclosure "
                    "under SEBI (LODR) Regulations 2015"
                ),
                target_authority="SEBI / NSE / BSE",
                legal_basis="SEBI (LODR) Regulations 2015, Regulation 30 (material disclosure)",
                impact_description=(
                    "Listed companies must disclose material litigation risks; "
                    "investor relations pressure is extremely effective"
                ),
            ))

        # ── 4. Criminal shadow (civil-only but creates fear) ─────────

        criminal_signals = ("fraud", "cheat", "scam", "fake", "counterfeit", "stolen",
                           "forged", "misrepresent", "deceive", "dupe")
        if any(k in corpus for k in criminal_signals):
            tactics.append(PressureTactic(
                tactic="Criminal Complaint Reservation",
                action=(
                    "Reserve the right to file a criminal complaint under Bharatiya Nyaya "
                    "Sanhita, 2023 (BNS) §318 (cheating) and/or §319 (cheating by personation) "
                    "and/or Information Technology Act, 2000 §66D (cheating by personation using "
                    "computer resource) if the conduct is found to constitute criminal fraud"
                ),
                target_authority="Police / Cyber Crime Cell",
                legal_basis="BNS 2023 §§318-319; IT Act 2000 §§66, 66D",
                impact_description=(
                    "Criminal complaint possibility creates strongest personal liability fear; "
                    "directors can be arrested; non-bailable offences under BNS are powerful deterrent"
                ),
            ))
        else:
            # Even without explicit fraud signals, reserve criminal rights softly
            tactics.append(PressureTactic(
                tactic="Reservation of Criminal Remedies",
                action=(
                    "Reserve the right to examine whether the conduct constitutes a "
                    "criminal offence under applicable provisions of the Bharatiya Nyaya "
                    "Sanhita, 2023 and/or the Information Technology Act, 2000, and to "
                    "file an appropriate first information report if warranted"
                ),
                target_authority="Police / Cyber Crime Cell",
                legal_basis="BNS 2023; IT Act 2000 (if applicable)",
                impact_description=(
                    "Even a reservation of criminal rights signals serious intent and "
                    "creates urgency for corporate legal teams to settle"
                ),
            ))

        # ── 5. CC strategy (copy to multiple stakeholders) ───────────

        cc_targets = ["Registered office of the company"]
        if not respondent_identity_found:
            cc_targets.append("Registrar of Companies, MCA")
        for industry in detected_industries:
            if industry == "banking_finance":
                cc_targets.append("RBI Ombudsman / Chief General Manager, RBI Consumer Education & Protection")
            elif industry == "ecommerce":
                cc_targets.append("Secretary, Department of Consumer Affairs, Government of India")
            elif industry == "telecom":
                cc_targets.append("Secretary, TRAI")
            elif industry == "airline_travel":
                cc_targets.append("Director General of Civil Aviation")
            elif industry == "real_estate":
                cc_targets.append("Chairman, State RERA Authority")
            elif industry == "insurance":
                cc_targets.append("Chairman, IRDAI")

        cc_targets.append("National Consumer Helpline (NCH)")

        tactics.append(PressureTactic(
            tactic="Multi-Stakeholder CC Strategy",
            action=(
                "Serve copies of this legal notice to: " + "; ".join(cc_targets) +
                ". This ensures regulatory awareness and creates compliance pressure "
                "from multiple directions simultaneously"
            ),
            target_authority=", ".join(cc_targets),
            legal_basis="Standard legal notice practice; regulatory awareness obligation",
            impact_description=(
                "Multi-directional service creates pressure from regulators, "
                "compliance teams, and senior management simultaneously — "
                "far more effective than a single-point notice"
            ),
        ))

        # ── Determine severity level ─────────────────────────────────
        severity = "standard"
        if len(tactics) > 8:
            severity = "elevated"
        if any(k in corpus for k in criminal_signals):
            severity = "maximum"

        summary = (
            f"{len(tactics)} pressure tactics identified across "
            f"{len(detected_industries)} industry sector(s) "
            f"({', '.join(detected_industries) if detected_industries else 'general consumer'}). "
            f"Severity level: {severity}. "
            f"These tactics are designed to create multi-directional compliance pressure "
            f"that makes resolution cheaper and easier than fighting."
        )

        return EscalationStrategy(
            tactics=tactics,
            severity_level=severity,
            summary=summary,
        )

    def _detect_industries(self, corpus: str) -> list[str]:
        detected: list[str] = []
        for industry, keywords in _INDUSTRY_SIGNALS.items():
            if any(k in corpus for k in keywords):
                detected.append(industry)
        return detected
