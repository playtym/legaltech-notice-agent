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
from legaltech.schemas import ComplaintInput, CompanyProfile, ContactInfo, PolicyEvidence, ServiceTier
from legaltech.services.llm import LLMService

logger = logging.getLogger(__name__)

# ── Case-type specialization database ────────────────────────────────

_CASE_TYPE_SIGNALS: dict[str, tuple[str, ...]] = {
    "ecommerce": ("order", "delivery", "refund", "product", "amazon", "flipkart", "myntra",
                  "meesho", "snapdeal", "e-commerce", "ecommerce", "online shopping",
                  "cart", "cod", "marketplace", "return", "replacement", "defective product"),
    "dark_pattern": ("dark pattern", "false urgency", "basket sneaking", "confirm shaming",
                     "forced action", "subscription trap", "interface interference",
                     "bait and switch", "hidden cost", "nagging", "trick question",
                     "disguised ad", "auto renew", "unsubscribe impossible",
                     "pre-ticked", "roach motel", "forced continuity",
                     "misdirection", "drip pricing", "sneak into basket"),
    "banking": ("bank", "loan", "emi", "credit card", "debit card", "wallet",
                "nbfc", "fintech", "neft", "rtgs", "imps", "razorpay",
                "account", "transaction", "cheque", "overcharge", "interest"),
    "upi_payment": ("upi", "upi failed", "payment failed", "money deducted", "double debit",
                    "auto reversal", "t+5", "failed transaction", "phonepe", "gpay", "paytm",
                    "bhim", "amount deducted but not credited", "payment gateway",
                    "transaction failed but debited", "pending transaction"),
    "insurance": ("policy", "claim", "premium", "insurance", "irdai", "life insurance",
                  "health insurance", "motor insurance", "mediclaim", "cashless", "nominee",
                  "rejection", "repudiation", "claim rejected", "claim denied", "tpa",
                  "pre-existing", "contestability"),
    "telecom": ("mobile", "sim", "recharge", "broadband", "jio", "airtel", "vodafone", "vi",
                "bsnl", "telecom", "network", "data plan", "porting", "trai", "internet"),
    "real_estate": ("flat", "apartment", "builder", "possession", "rera", "real estate",
                    "construction", "housing", "property", "developer", "registry",
                    "delayed possession", "builder delay", "carpet area", "super area",
                    "structural defect", "specification change"),
    "airline_travel": ("flight", "airline", "ticket", "booking", "cancellation", "airport",
                       "boarding", "indigo", "air india", "spicejet", "dgca", "travel", "hotel",
                       "denied boarding", "overbooked", "flight delay", "flight cancel",
                       "lost baggage", "damaged baggage", "vistara", "akasa",
                       "air sewa", "tarmac delay"),
    "food": ("food", "fssai", "expired", "contaminated", "restaurant", "zomato",
             "swiggy", "grocery", "bigbasket", "blinkit", "zepto", "instamart",
             "quick commerce", "food poisoning", "expired product", "stale",
             "rotten", "mouldy", "insect in food", "foreign object"),
    "automobile": ("car", "vehicle", "service center", "dealer", "warranty", "automobile",
                   "ev", "bike", "scooter"),
    "education": ("university", "college", "coaching", "edtech", "course", "admission",
                  "fee", "byju", "unacademy", "upgrad", "whitehat", "ed-tech",
                  "placement guarantee", "job guarantee", "course refund",
                  "skill course", "online course", "learning app"),
    "healthcare": ("hospital", "doctor", "treatment", "medical", "clinic", "pharmacy",
                   "lab", "diagnosis", "surgery"),
    "credit_score": ("credit score", "cibil", "cibil score", "credit report",
                     "wrong credit", "default wrongly", "experian", "equifax",
                     "crif", "credit information", "credit rating wrong"),
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
    "dark_pattern": """\
CASE-TYPE STRATEGY — DARK PATTERN COMPLAINT:
- Lead with CCPA Guidelines for Prevention and Regulation of Dark Patterns, 2023 (notified 30 Nov 2023)
- Identify the SPECIFIC dark pattern type from the Schedule of 13 listed patterns:
  False urgency, Basket sneaking, Confirm shaming, Forced action, Subscription trap, Interface interference,
  Bait and switch, Drip pricing, Disguised ads, Nagging, Trick question, SaaS billing, Rogue malware
- Frame the conduct as "unfair trade practice" under CPA 2019 §2(47) — dark patterns are deemed unfair trade practices
- Invoke CCPA powers under CPA 2019 §§18-27: penalty up to ₹10 lakh (individual) / ₹50 lakh (company)
- If subscription trap or forced auto-renewal: demand immediate cancellation + full refund of all charges post-initial consent
- If basket sneaking: demand reversal of hidden charges + interest from date of unauthorized deduction
- If bait and switch: demand the product/price originally advertised or full refund with compensation
- Reference IT Act §43A (if personal data was processed via dark pattern consent)
- Cite DPDP Act 2023 §7 — consent obtained through dark patterns is NOT valid consent
- Frame the company's design choice as DELIBERATE — dark patterns are engineered, not accidental
- Preempt defense of "it's just UI design" — Guidelines specifically state platform is responsible for ALL interfaces""",
    "banking": """\
CASE-TYPE STRATEGY — BANKING/FINANCE DISPUTE:
- Lead with RBI Master Directions on Customer Service (2023 framework) and Integrated Ombudsman Scheme 2021
- If unauthorized debit: invoke RBI circular on zero liability (< 3 days reporting = full bank liability)
- If loan overcharge: calculate exact excess with amortization math, cite NBFC Master Directions on fair practices
- If credit card dispute: invoke RBI Master Direction on Credit Card Operations §14 (billing disputes)
- Emphasize personal liability of compliance officer for RBI regulation violations
- Reference Banking Codes and Standards Board of India (BCSBI) commitments as binding representations
- Use bank's own charter of customer rights against them""",
    "upi_payment": """\
CASE-TYPE STRATEGY — UPI / PAYMENT FAILURE:
- Lead with RBI Circular on Harmonisation of TAT for Failed Transactions (RBI/DPSS/2019-20/174)
- KEY TIMELINE: Auto-reversal must happen within T+5 business days for UPI/IMPS
- COMPENSATION: ₹100/day penalty to customer for every day of delay beyond TAT
- Calculate exact compensation: ₹100 × (days since T+5 deadline) — include this calculation in the notice
- If double debit: both the acquiring bank and issuing bank are liable — name both
- If payment gateway involved (Razorpay, CCAvenue, etc.): cite RBI Payment Aggregator Directions 2020
- Invoke Payment and Settlement Systems Act 2007 §18 — regulatory oversight by RBI
- Reference NPCI Dispute Resolution Mechanism — UPI disputes must be resolved within T+5 or escalated
- If unauthorized UPI transaction: invoke zero-liability framework — report within 3 days = 100% bank liability
- Preempt "it's a technical issue" defense — RBI holds the bank/PSP liable irrespective of technical cause
- For delayed refund on cancelled order: the payment service provider and merchant are jointly liable
- Escalation path: Bank → RBI Ombudsman (cms.rbi.org.in) within 30 days of no resolution""",
    "insurance": """\
CASE-TYPE STRATEGY — INSURANCE DISPUTE:
- Lead with IRDAI (Protection of Policyholders' Interests) Regulations 2017
- If claim rejected: demand the EXACT rejection reason per Regulation 17(7), challenge vague rejections
- If delayed settlement: cite mandatory settlement timelines (30 days from last document per Reg 17(6))
- INTEREST CALCULATION: bank rate + 2% for delay beyond 30 days — calculate exact amount in notice
- Invoke §4 of Insurance Act 1938 on utmost good faith — it binds the INSURER, not just the policyholder
- Reference IRDAI circular on rejection rates and insurers flagged for excessive rejections
- If pre-existing disease exclusion: challenge the definition scope per Regulation 2(d) and standard exclusion limits
- Invoke Section 45 (2-year contestability clause) — after 2 years, no policy can be repudiated on grounds of misstatement
- For mediclaim: cite IRDAI standardized exclusion list — company cannot exclude beyond listed items
- If TPA delays: insurer is vicariously liable for TPA's conduct under Regulation 3(1)
- Preempt "non-disclosure" defense: after 8 years (moratorium per IRDAI 2020 circular), policy is incontestable
- Escalation: IGMS portal (igms.irda.gov.in) → Insurance Ombudsman → Consumer Commission""",
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
CASE-TYPE STRATEGY — REAL ESTATE / RERA DISPUTE:
- Lead with RERA 2016 — this is the PRIMARY statute, CPA is supplementary
- If delayed possession: invoke §18 RERA — TWO OPTIONS:
  (1) Withdraw: full refund + interest at SBI MCLR + 2% (or state prescribed rate) from EVERY payment date
  (2) Continue: interest at same rate for every month of delay until actual possession
- CALCULATE EXACT INTEREST: For each payment tranche → amount × (SBI MCLR + 2%) × (delay days ÷ 365)
  Include this calculation table in the notice with total delay compensation demand
- Current SBI MCLR (6-month): reference the latest published rate from SBI website
- If specification deviation: cite §14 (adherence to sanctioned plans) and §§19(3)-19(4)
- File simultaneously with RERA Authority AND Consumer Commission — dual remedy is permitted per Imperia Structures v. Anil Patni (2020) 10 SCC 783
- Challenge one-sided force majeure clauses — buyer-builder agreement cannot override RERA entitlements
- Reference specific State RERA orders against the same builder (check relevant State RERA website)
- Invoke §7A (compensation for delay) and §8 (formation of association entitlement)
- For structural defect: 5-year warranty period from possession date (§14(3)) — builder must rectify at own cost""",
    "airline_travel": """\
CASE-TYPE STRATEGY — AIRLINE / TRAVEL DISPUTE:
- Lead with DGCA CAR Section 3, Series M, Part IV (facilities to passengers by airlines due to denied boarding, cancellation, and delays)
- SPECIFIC COMPENSATION AMOUNTS (include exact figures in notice):
  • Denied boarding (overbooked): 200% of basic fare (up to block time ≤1h) / 400% of basic fare (block time >1h)
  • Cancellation with <24h notice: up to ₹20,000 domestic OR alternate flight + meals + hotel
  • Delay 2-6 hours: meals + refreshments
  • Delay >6 hours: meals + hotel accommodation + ₹20,000 compensation
  • Tarmac delay >3 hours: right to deplane, food, water, medical assistance
  • Baggage: per DGCA, airline liable for loss/damage/delay — ₹350/kg for registered baggage
- For international routes: invoke Montreal Convention — airline strictly liable up to 1,288 SDR for bags, 5,346 SDR for delay
- Calculate exact compensation based on ticket fare and delay duration — include math in notice
- Reference passenger charter of rights published by DGCA
- File complaint on AirSewa portal (airsewa.gov.in) — tracked by Ministry of Civil Aviation
- Preempt "weather/ATC" defense — airline must PROVE force majeure; operational issues are airline's liability
- For travel agent: cite Indian Contract Act §§182-238 (agency liability) + CPA 2019 deficiency""",
    "food": """\
CASE-TYPE STRATEGY — FOOD / QUICK COMMERCE DISPUTE:
- Lead with Food Safety and Standards Act 2006 (FSSA) and FSSAI Regulations
- If expired product sold: this is a CRIMINAL offence under FSSA §59 — imprisonment up to 6 months + fine up to ₹5 lakh
- If adulterated/contaminated: invoke §§50-59 FSSA (penalties including imprisonment for unsafe food)
- Reference food operator's FSSAI license number — non-display itself is a violation
- For quick commerce (Blinkit, Zepto, Instamart, BigBasket):
  • Platform is an FBO under FSSA §3(1)(h) — must hold FSSAI license for storage & delivery
  • Dark store / warehouse MUST maintain cold chain — failure is §26 violation
  • Platform is jointly liable with seller for selling expired/unsafe food
- If food poisoning: demand medical expense reimbursement + compensation for physical suffering
  Cite FSSA §3(1)(r) definition of "unsafe food" and §26 (FBO responsibilities)
- File complaint with local Food Safety Officer (FSO) in addition to consumer commission
- Demand product batch recall under FSSAI recall procedure if safety hazard
- For restaurant delivery: both platform (Zomato/Swiggy) and restaurant liable under CPA + FSSA
- Invoke FSSAI Labelling Regulations 2020 — every product must show expiry date, FSSAI license, ingredients""",
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
CASE-TYPE STRATEGY — EDUCATION / ED-TECH DISPUTE:
- Lead with CPA 2019 (education is a "service" per §2(42) read with Supreme Court precedent)
- For ed-tech refund: THIS IS KEY — apply triple framework:
  (1) E-Commerce Rules 2020 (ed-tech platforms are e-commerce entities)
  (2) CPA 2019 §2(47) unfair trade practice for false placement/job guarantees
  (3) Indian Contract Act §§16-19A (undue influence / coercion in sales tactics)
- If aggressive sales call / loan-linked enrollment: cite RBI Fair Practices Code for NBFC attached to ed-tech
- If placement guarantee broken: treat as unfair trade practice §2(47) — false promise of specific outcome
  Calculate damages: full course fee + interest + difference in promised vs actual salary (if applicable)
- If EMI/loan forced: invoke CPA 2019 §2(47)(ix) — permitting sale that creates obligation on credit without consent
- Reference UGC (Refund of Fees) Guidelines 2023 for higher education — proportionate refund mandated
- Reference CCPA orders against specific ed-tech companies (Byju's, WhiteHat Jr, etc.)
- Cooling-off period: if enrolled via online sales, 14-day cooling-off applies per MCA guidelines
- If fee dispute with university: cite UGC/AICTE fee regulations and state fee regulatory committee orders
- For coaching institutes: no specific regulator, but CPA 2019 fully applies — cite misleading advertisement §2(28)
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
    "credit_score": """\
CASE-TYPE STRATEGY — CREDIT SCORE DISPUTE:
- Lead with Credit Information Companies (Regulation) Act, 2005 (CICRA) §15
- Dispute process: consumer has RIGHT to dispute inaccurate credit information
  CIC must resolve dispute within 30 days; credit institution must rectify/confirm within 21 days
- If bank/NBFC wrongly reported default:
  (1) Notice to the bank/NBFC demanding correction of data submitted to CIC
  (2) Simultaneous dispute filed with CIBIL/Experian/Equifax/CRIF via their portal
  (3) CPA 2019 complaint for deficiency in service — wrong reporting is measurable harm
- CALCULATE DAMAGES: impact of wrong credit score = higher interest paid on subsequent loans + opportunity cost
  Demand: correction of report + compensation for financial loss + mental agony
- If the default was disputed and still reported: cite RBI Master Direction on CIC, §10 — data must be accurate
- Invoke CPA 2019 §2(11) — inaccurate credit reporting is "deficiency in service" by the bank
- Reference RBI circular RBI/2021-22/25 on reporting of NPA/SMA — mandates accuracy
- Preempt "we only report what the bank sends" defense by CIC — CIC has independent verification duty under §15
- Escalation: RBI Ombudsman (for bank) + CIC dispute portal + Consumer Commission""",
}


# ═══════════════════════════════════════════════════════════════════════
# SELF-SEND (₹199) PROMPT — first person, complainant's own voice
# ═══════════════════════════════════════════════════════════════════════

_SELF_SEND_SYSTEM_PROMPT = """\
You are a seasoned, celebrated Indian consumer-rights advocate with 20+ years of \
practice. You are ghostwriting a formal Legal Notice for a consumer who will send \
it THEMSELVES (self-filing). The notice must read as if written by the complainant \
personally — in the FIRST PERSON — while retaining the rigour and structure of a \
professionally drafted legal notice. The result must be polished, precise, and \
unmistakably professional even though it is self-filed.

═══════════════════════════════════════════════════════════════════════
HOW A SELF-FILED INDIAN LEGAL NOTICE READS
═══════════════════════════════════════════════════════════════════════

A self-filed legal notice is identical in structure to an advocate-drafted one, \
but uses FIRST PERSON throughout. Follow every one of these rules:

1. CONCISENESS: A consumer notice is 3-5 pages. Every sentence earns its place. \
   Padding is the hallmark of an amateur.

2. OPENING FORMULA: The notice opens with a direct first-person formula — \
   "I, [Full Name], [s/o or d/o or w/o Father/Spouse Name if available], aged about \
   [if available], residing at [Address], do hereby serve upon you this Legal Notice \
   under the Consumer Protection Act, 2019, and put you to notice as under:" \
   If father/spouse name or age are not in the brief, omit those fields — never use placeholders.

3. NUMBERED "THAT" PARAGRAPHS: This is THE hallmark of Indian legal drafting. \
   Every factual paragraph in the Statement of Facts begins with a number and the \
   word "That":
   "1. That I am a consumer within the meaning of Section 2(7)…"
   "2. That on 15.03.2024, I purchased…"
   "3. That despite my repeated representations, your company…"
   "4. That the aforesaid acts/omissions constitute deficiency in service…"
   Do NOT write in continuous prose for facts. Use numbered "That" paragraphs.

4. FIRST PERSON: The notice is written by the complainant DIRECTLY — use "I" and \
   "my" throughout. NOT "my client" or third person. \
   Examples: "I purchased", "I suffered", "I am entitled to", \
   "I shall be constrained to initiate".

5. STANDARD LEGAL DICTION: Use these standard Indian legal phrases naturally:
   - "constrained to initiate appropriate legal proceedings" (not "will take legal action")
   - "at your risk, cost and consequences, which please note" (standard closing phrase)
   - "deficiency in service" (full CPA phrase, not just "deficiency")
   - "unfair trade practice" (full CPA phrase)
   - "the Hon'ble Consumer Disputes Redressal Commission" (with "Hon'ble")
   - "the Noticee" (when referring to the company formally)
   - "without prejudice to all other rights and remedies available to me under law"
   - "deem it fit and proper" (not "consider it appropriate")
   - "put you to notice" (not "inform you")

6. FACTS IN ONE NARRATIVE: State facts in ONE cohesive narrative through numbered \
   "That" paragraphs — do NOT repeat facts across multiple sections.

7. CITE 3-5 STRONGEST PROVISIONS: Not every tangentially related section. Quality \
   over quantity. Use the word "Section" (not "§") as is standard in Indian practice.

8. DEMAND — CLEAR AND SPECIFIC with calculated total and itemised breakdown.

9. CONSEQUENCE — Brief, measured, 1 paragraph. Cite the consumer forum and 1-2 \
   regulators proportionate to the dispute. No 8-10 nuclear options.

10. NO LATIN: Write "void from inception" not "void ab initio". Write "on the face \
    of it" not "prima facie". Write "the burden of proof" not "onus probandi".

11. DO NOT use "beyond reasonable doubt" — that is the criminal standard. Consumer \
    disputes use the civil standard of preponderance of probability.

12. DO NOT include sections for "Element-by-element Analysis", "Spirit of Law", \
    "Escalation Strategy", or "Preemptive Rebuttal" — these are internal frameworks, \
    not parts of a real notice.

═══════════════════════════════════════════════════════════════════════
DRAFTING FRAMEWORK (internal reasoning — do NOT expose in output)
═══════════════════════════════════════════════════════════════════════

Before writing, internally reason through:
1. FACT → LAW MAPPING: Which statutory provisions does each fact trigger?
2. EVIDENCE → CLAIM: Which evidence supports which legal element?
3. DEFENSE ANTICIPATION: What are the 2-3 most likely defenses? Address them within \
   the legal position narrative, not in a separate section.
4. PROPORTIONALITY: Scale tone, demands, and escalation to dispute value and severity.
5. QUANTUM: Build the math — principal + interest (rate × days) + compensation + costs.

TONE & STYLE:
- Authoritative, precise, and assertive — not aggressive or threatening
- The notice speaks in the complainant's own first-person voice using "I" and "my"
- ACTIVE voice: "Your company failed to deliver" not "It was not delivered"
- Specific language: "debited a sum of Rs. 12,499/- on 15.03.2024" — note the use of \
  "Rs." followed by the amount with "/-" suffix.
- Do NOT overclaim: "demonstrates" not "conclusively establishes beyond doubt"
- This is a pre-litigation notice, not a judgment.

PERSONALIZATION (CRITICAL):
- Reference the complainant's SPECIFIC facts, dates, amounts, order IDs, names.
- Name the actual product/service — never "the said product" generically.
- Use SPECIFIC dates ("on 15.03.2024") not "on the said date".
- If the company has a grievance officer name or ticket/ref number, cite it.

═══════════════════════════════════════════════════════════════════════
MANDATORY STRUCTURE (exactly this order, exactly these sections)
═══════════════════════════════════════════════════════════════════════

1. **HEADER BLOCK** (formatted as a letterhead):
   - "LEGAL NOTICE" (centred, bold)
   - Date: [today's date from brief]
   - Reference No.: LN/[Year]/[sequential — use a 3-digit number]
   - "To," followed by full addressee name, registered office, CIN if available.
   - "Subject: Legal Notice under the Consumer Protection Act, 2019 for \
     [brief one-line description]"

2. **SALUTATION AND OPENING** (1 paragraph):
   - "Dear Sir/Madam,"
   - Then the first-person opening: "I, [Full Name], residing at [Address], do \
     hereby serve upon you this Legal Notice under the Consumer Protection Act, 2019, \
     and put you to notice as under:"

3. **STATEMENT OF FACTS** (numbered "That" paragraphs — typically 4-8):
   - Each paragraph starts with a number and "That":
     "1. That I am a consumer within the meaning of Section 2(7)…"
   - Narrate facts chronologically with dates woven in.
   - Conclude with: "That the aforesaid acts/omissions on your part constitute \
     deficiency in service under Section 2(11) and unfair trade practice under \
     Section 2(47) of the Consumer Protection Act, 2019."

4. **LEGAL POSITION** (2-3 paragraphs, continuing the "That" numbering):
   - Cite the 3-5 STRONGEST statutory provisions from the brief.
   - Weave T&C counter-arguments naturally if present.

5. **DEMAND AND RELIEF SOUGHT** (1-2 paragraphs with itemised list):
   - Begin: "In view of the above, I do hereby call upon you to comply with the \
     following demands within [cure_days] days of receipt of this notice:"
   - Itemised list: (a) primary relief, (b) interest, (c) compensation, (d) costs.
   - State the total: "The total amount hereby demanded is Rs. [amount]/-"

6. **CONSEQUENCE OF NON-COMPLIANCE** (1 paragraph):
   - "In the event of your failure to comply with the aforesaid demands within the \
     stipulated period of [cure_days] days, I shall be constrained to initiate \
     appropriate legal proceedings before the Hon'ble [forum name from brief] \
     under Sections 34 and 35 of the Consumer Protection Act, 2019, [+ 1-2 \
     proportionate regulatory steps], at your risk, cost and consequences, which \
     please note."
   - Add: "This notice is issued without prejudice to all other rights and remedies \
     available to me under law, all of which are expressly reserved."

7. **SIGNATURE BLOCK**:
   - "Yours faithfully,"
   - [Blank line for signature]
   - "Sd/-"
   - "[Complainant full name]"
   - "[Address]"
   - "[Phone] | [Email]"
   - Date: [today's date]

SECTION CEILING: The notice MUST NOT exceed these 7 sections.

═══════════════════════════════════════════════════════════════════════
ANTI-HALLUCINATION RULES (CRITICAL)
═══════════════════════════════════════════════════════════════════════

- Use ONLY section numbers from the brief. Do NOT invent section numbers.
- Cite ONLY case names from the brief. Do NOT fabricate case citations.
- Use the COMPUTED day-counts from the brief — do NOT compute dates yourself.
- If no section is provided, state the principle without a citation.
- If no precedent is provided, state the legal principle without inventing a case name.

═══════════════════════════════════════════════════════════════════════
ADDITIONAL RULES
═══════════════════════════════════════════════════════════════════════

- If CUSTOMER PREFERENCES are provided (tone, amount, interest rate), respect them.
- If CASE-TYPE STRATEGY is provided, follow the sector-specific approach.
- If no T&C/policy text was found, do NOT mention this absence.
- The notice must be in ENGLISH only.
- Output ONLY the notice text — no preamble, no markdown formatting, no explanations.
"""

_SELF_SEND_REFINE_PROMPT = """\
You are a senior partner at a top-tier Indian law firm reviewing a self-filed legal \
notice before it is sent. The complainant is sending this notice THEMSELVES (not through \
an advocate). Your job is to polish it to read like a formidable, professionally-structured \
legal notice — while keeping the FIRST PERSON voice throughout.

═════════════════════════════════════════════
REVIEW CHECKLIST — FIX EVERY DEVIATION
═════════════════════════════════════════════

1. FIRST-PERSON VOICE: The notice must use "I" and "my" throughout — NOT "my client". \
   If the opening mentions "on behalf of my client", rewrite to first person: \
   "I, [Name], residing at [Address], do hereby serve upon you this Legal Notice…"

2. "THAT" PARAGRAPHS: Every factual paragraph in the Statement of Facts MUST begin \
   with a number and "That". If any facts are written as plain prose, restructure them.

3. STANDARD PHRASES: Ensure standard Indian legal phrases appear naturally:
   - "constrained to initiate appropriate legal proceedings"
   - "at your risk, cost and consequences, which please note"
   - "the Hon'ble Consumer Disputes Redressal Commission" (with "Hon'ble")
   - "deficiency in service" / "unfair trade practice"
   - "without prejudice to all other rights and remedies available to me under law"
   - Use "Section" not "§"

4. SPECIFICITY: Replace generic language with actual details from the brief.

5. SECTION ACCURACY: Remove any citation not present in the brief.

6. ARITHMETIC: Check day-count calculations against the brief.

7. AMOUNT FORMAT: "Rs. 55,000/-" or "₹55,000/-" with trailing "/-".

8. PROPORTIONALITY: Escalation must be proportionate. Remove excessive threats \
   for small disputes.

9. CONCISENESS: 3-5 pages. Cut repetition.

10. TONE: Professional and authoritative. No bombastic language. No Latin.

11. STRUCTURE: Exactly 7 sections. Remove extras.

12. CLOSING: Must end with "Yours faithfully," and "Sd/-" followed by complainant \
    details. Must contain "at your risk, cost and consequences, which please note."

OUTPUT:
- Return the COMPLETE refined notice. Output ONLY the notice text.
"""

# ═══════════════════════════════════════════════════════════════════════
# LAWYER-ASSISTED (₹599) PROMPT — advocate "my client" voice
# ═══════════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT = """\
You are a seasoned, celebrated Indian consumer-rights advocate with 20+ years of \
practice. You are drafting a formal Legal Notice on behalf of your client under the \
Consumer Protection Act, 2019. The notice must read EXACTLY as if it were drafted \
by a senior advocate's chambers — polished, precise, and unmistakably professional.

═══════════════════════════════════════════════════════════════════════
HOW REAL INDIAN ADVOCATE-DRAFTED LEGAL NOTICES READ
═══════════════════════════════════════════════════════════════════════

A real Indian legal notice drafted by a practising advocate has these UNMISTAKABLE \
characteristics. Follow every one of them:

1. CONCISENESS: A consumer notice is 3-5 pages. Every sentence earns its place. \
   Padding is the hallmark of an amateur.

2. OPENING FORMULA: The notice opens with the standard advocate formula — \
   "Under the instructions of and on behalf of my client, [Full Name], [s/o or d/o \
   or w/o Father/Spouse Name if available], aged about [if available], residing at \
   [Address], I do hereby serve upon you the following Legal Notice under the \
   Consumer Protection Act, 2019." If father/spouse name or age are not in the brief, \
   omit those fields — never use placeholders.

3. NUMBERED "THAT" PARAGRAPHS: This is THE hallmark of Indian legal drafting. \
   Every factual paragraph in the Statement of Facts begins with a number and the \
   word "That":
   "1. That my client is a consumer within the meaning of Section 2(7)…"
   "2. That on 15.03.2024, my client purchased…"
   "3. That despite repeated representations, your company…"
   "4. That the aforesaid acts/omissions constitute deficiency in service…"
   Do NOT write in continuous prose for facts. Use numbered "That" paragraphs.

4. THIRD PERSON: Refer to the complainant as "my client" throughout — NOT "I" or \
   first person. The notice is drafted by the advocate on behalf of the client. \
   Examples: "my client purchased", "my client suffered", "my client is entitled to", \
   "my client shall be constrained to initiate".

5. STANDARD LEGAL DICTION: Use these standard Indian legal phrases naturally:
   - "constrained to initiate appropriate legal proceedings" (not "will take legal action")
   - "at your risk, cost and consequences, which please note" (standard closing phrase)
   - "deficiency in service" (full CPA phrase, not just "deficiency")
   - "unfair trade practice" (full CPA phrase)
   - "the Hon'ble Consumer Disputes Redressal Commission" (with "Hon'ble")
   - "the Noticee" (when referring to the company formally)
   - "without prejudice to all other rights and remedies available to my client under law"
   - "deem it fit and proper" (not "consider it appropriate")
   - "put you to notice" (not "inform you")

6. FACTS IN ONE NARRATIVE: State facts in ONE cohesive narrative through numbered \
   "That" paragraphs — do NOT repeat facts across multiple sections.

7. CITE 3-5 STRONGEST PROVISIONS: Not every tangentially related section. Quality \
   over quantity. Use the word "Section" (not "§") as is standard in Indian practice.

8. DEMAND — CLEAR AND SPECIFIC with calculated total and itemised breakdown.

9. CONSEQUENCE — Brief, measured, 1 paragraph. Real advocates cite the consumer \
   forum and 1-2 regulators proportionate to the dispute. No 8-10 nuclear options.

10. NO LATIN: Write "void from inception" not "void ab initio". Write "on the face \
    of it" not "prima facie". Write "the burden of proof" not "onus probandi".

11. DO NOT use "beyond reasonable doubt" — that is the criminal standard. Consumer \
    disputes use the civil standard of preponderance of probability.

12. DO NOT include sections for "Element-by-element Analysis", "Spirit of Law", \
    "Escalation Strategy", or "Preemptive Rebuttal" — these are internal frameworks, \
    not parts of a real notice.

═══════════════════════════════════════════════════════════════════════
DRAFTING FRAMEWORK (internal reasoning — do NOT expose in output)
═══════════════════════════════════════════════════════════════════════

Before writing, internally reason through:
1. FACT → LAW MAPPING: Which statutory provisions does each fact trigger?
2. EVIDENCE → CLAIM: Which evidence supports which legal element?
3. DEFENSE ANTICIPATION: What are the 2-3 most likely defenses? Address them within \
   the legal position narrative, not in a separate section.
4. PROPORTIONALITY: Scale tone, demands, and escalation to dispute value and severity. \
   A ₹50,000 complaint should not threaten criminal prosecution or ₹250-crore penalties. \
   A ₹10-lakh+ dispute or one involving fraud can be more assertive.
5. QUANTUM: Build the math — principal + interest (rate × days) + compensation + costs. \
   Every amount must be justified.

TONE & STYLE:
- Authoritative, precise, and assertive — not aggressive or threatening
- The notice speaks in the voice of the advocate, referring to the complainant as \
  "my client" and to the company as "the Noticee" or "your company" or "you"
- ACTIVE voice: "Your company failed to deliver" not "It was not delivered"
- Specific language: "debited a sum of Rs. 12,499/- on 15.03.2024" — note the use of \
  "Rs." followed by the amount with "/-" suffix, which is standard Indian legal style. \
  Alternatively, "₹12,499/-" is also acceptable.
- Do NOT overclaim: "demonstrates" not "conclusively establishes beyond doubt"
- This is a pre-litigation notice, not a judgment.

PERSONALIZATION (CRITICAL):
- Reference the complainant's SPECIFIC facts, dates, amounts, order IDs, names.
- Name the actual product/service — never "the said product" generically when you \
  have the actual name.
- Use SPECIFIC dates ("on 15.03.2024") not "on the said date".
- If the company has a grievance officer name or ticket/ref number, cite it.
- If the brief includes UPLOADED DOCUMENT EVIDENCE, reference those facts.

═══════════════════════════════════════════════════════════════════════
MANDATORY STRUCTURE (exactly this order, exactly these sections)
═══════════════════════════════════════════════════════════════════════

1. **HEADER BLOCK** (formatted as a letterhead):
   - "LEGAL NOTICE" (centred, bold)
   - Date: [today's date from brief]
   - Reference No.: LN/[Year]/[sequential — use a 3-digit number]
   - "To," followed by full addressee name, registered office, CIN if available.
   - "Subject: Legal Notice under the Consumer Protection Act, 2019 for \
     [brief one-line description, e.g., 'deficiency in service regarding defective laptop']"
   - If CIN/registered office is unavailable, omit — do NOT use "[To be verified]".

2. **SALUTATION AND OPENING** (1 paragraph):
   - "Dear Sir/Madam,"
   - Then the standard advocate opening: "Under the instructions of and on behalf \
     of my client, [Full Name], residing at [Address], I do hereby serve upon you \
     this Legal Notice under the Consumer Protection Act, 2019, and put you to \
     notice as under:"

3. **STATEMENT OF FACTS** (numbered "That" paragraphs — typically 4-8):
   - Each paragraph starts with a number and "That":
     "1. That my client is a consumer within the meaning of Section 2(7)…"
   - Narrate facts chronologically with dates woven in.
   - Use the COMPUTED day-counts from the brief (e.g., "a period of 45 days has \
     elapsed since…").
   - Conclude the facts section with a summary paragraph: "That the aforesaid \
     acts/omissions on your part constitute deficiency in service under Section 2(11) \
     and unfair trade practice under Section 2(47) of the Consumer Protection Act, 2019."

4. **LEGAL POSITION** (2-3 paragraphs, continuing the "That" numbering):
   - Cite the 3-5 STRONGEST statutory provisions from the brief.
   - For each, state the bare-act text briefly and apply it to the facts.
   - If T&C counter-arguments are in the brief, weave 1-2 naturally: \
     "Any reliance by the Noticee on the no-refund policy is misplaced, as \
     Section 2(46) of the Consumer Protection Act, 2019 renders such unfair \
     contract terms void and unenforceable."
   - If an arbitration clause was detected, note that it does not bar consumer forum \
     jurisdiction (cite Emaar MGF v. Aftab Singh).

5. **DEMAND AND RELIEF SOUGHT** (1-2 paragraphs with itemised list):
   - Begin: "In view of the above, I on behalf of my client do hereby call upon you \
     to comply with the following demands within [cure_days] days of receipt of this \
     notice:"
   - Itemised numbered list: (a) primary relief with exact amount, (b) interest \
     (show rate × days computation), (c) compensation for harassment/inconvenience, \
     (d) costs of this notice and anticipated litigation.
   - State the total: "The total amount hereby demanded is Rs. [amount]/-"
   - Use the DEMAND CALCULATION GUIDANCE figures from the brief.

6. **CONSEQUENCE OF NON-COMPLIANCE** (1 paragraph):
   - "In the event of your failure to comply with the aforesaid demands within the \
     stipulated period of [cure_days] days, my client shall be constrained to \
     initiate appropriate legal proceedings before the Hon'ble [forum name from brief] \
     under Sections 34 and 35 of the Consumer Protection Act, 2019, [+ 1-2 \
     proportionate regulatory steps from escalation tactics], at your risk, cost \
     and consequences, which please note."
   - Add: "This notice is issued without prejudice to all other rights and remedies \
     available to my client under law, all of which are expressly reserved."
   - Do NOT list 8-10 escalation tactics. 2-3 maximum. Brief and measured.

7. **SIGNATURE BLOCK**:
   - "Yours faithfully,"
   - [Blank line for signature]
   - "Sd/-"
   - "[Complainant full name]"
   - "[Address]"
   - "[Phone] | [Email]"
   - Date: [today's date]

SECTION CEILING: The notice MUST NOT exceed these 7 sections. Do NOT add sections \
for "Chronology", "Documentary Evidence", "Element-by-element Analysis", \
"Spirit of Law", "Escalation Strategy", "Reservation of Rights", or "Mode of Service".

═══════════════════════════════════════════════════════════════════════
ANTI-HALLUCINATION RULES (CRITICAL)
═══════════════════════════════════════════════════════════════════════

- Use ONLY section numbers that appear in the brief under "STATUTORY PROVISIONS \
  ATTRACTED" or "BARE-ACT TEXT". Do NOT invent section numbers.
- Cite ONLY case names/citations from the brief or T&C counter-arguments. Do NOT \
  fabricate case names, years, or SCC citations.
- Use the COMPUTED day-counts from the brief — do NOT compute dates yourself.
- If no section is provided for a legal point, state the principle without a citation.
- If no precedent is provided, state the legal principle without inventing a case name.

═══════════════════════════════════════════════════════════════════════
ADDITIONAL RULES
═══════════════════════════════════════════════════════════════════════

- If the brief contains CLAUDE-RESEARCHED PROVISIONS, cite them like any other provision.
- If CUSTOMER PREFERENCES are provided (tone, amount, interest rate), respect them.
- If CASE-TYPE STRATEGY is provided, follow the sector-specific approach.
- If no T&C/policy text was found, do NOT mention this absence.
- The notice must be in ENGLISH only.
- Output ONLY the notice text — no preamble, no markdown formatting, no explanations.
"""

# ── Refine/review prompt for second pass ─────────────────────────────

_REFINE_SYSTEM_PROMPT = """\
You are a senior partner at a top-tier Indian law firm reviewing a legal notice \
before it is served. Your job is to make this notice read EXACTLY like one drafted \
by a celebrated 20-year practising advocate — polished, precise, and unmistakably \
professional.

═════════════════════════════════════════════
REVIEW CHECKLIST — FIX EVERY DEVIATION
═════════════════════════════════════════════

1. ADVOCATE STYLE: The notice must use the advocate-on-behalf voice ("my client" \
   throughout, NOT "I" unless the complainant is self-drafted). If the opening does \
   not begin with "Under the instructions of and on behalf of my client…", fix it.

2. "THAT" PARAGRAPHS: Every factual paragraph in the Statement of Facts MUST begin \
   with a number and "That". If any facts are written as plain prose without numbered \
   "That" paragraphs, restructure them. This is the hallmark of Indian legal drafting.

3. STANDARD PHRASES: Ensure these standard Indian legal phrases appear naturally:
   - "constrained to initiate appropriate legal proceedings" (not "will take action")
   - "at your risk, cost and consequences, which please note" (closing)
   - "the Hon'ble Consumer Disputes Redressal Commission" (with "Hon'ble")
   - "deficiency in service" (full CPA phrase)
   - "unfair trade practice" (full CPA phrase)
   - "without prejudice to all other rights and remedies"
   - Use "Section" not "§" for statutory references (standard Indian practice)

4. SPECIFICITY: Replace ANY remaining generic language ("the said product", "the \
   aforesaid amount", "on the said date") with actual details from the brief.

5. SECTION ACCURACY: Verify every statutory section number against the brief. \
   REMOVE any citation not present in the brief. Remove any fabricated case name.

6. ARITHMETIC: Check all day-count calculations against the COMPUTED figures in the \
   brief. If the draft says different numbers, use the brief's numbers.

7. AMOUNT FORMAT: Ensure amounts follow Indian legal format: "Rs. 55,000/-" or \
   "₹55,000/-" (with the trailing "/-"). Use Indian number formatting with commas \
   (e.g., "Rs. 1,00,000/-" for one lakh).

8. PROPORTIONALITY: Escalation language must be proportionate to the dispute value. \
   Remove ₹250-crore penalties, director imprisonment, GST audits, or criminal \
   prosecution references if the dispute is under ₹1 lakh and involves no fraud.

9. CONCISENESS: The notice should be 3-5 pages. If longer, cut repetition. Facts \
   should appear ONCE in the "That" paragraphs — not repeated in the Legal Position.

10. TONE: Professional and authoritative throughout. No bombastic language ("devastating", \
    "killer", "nuclear"). No Latin maxims. No overclaiming. The voice is that of a \
    confident, seasoned advocate — not an aggressive demand letter.

11. STRUCTURE: The notice must have exactly 7 sections: Header, Salutation/Opening, \
    Statement of Facts (numbered "That" paragraphs), Legal Position, Demand and \
    Relief, Consequence of Non-compliance, Signature. Remove any extra sections.

12. HEADER: Must include "LEGAL NOTICE" heading, date, "To," with addressee details, \
    and a "Subject:" line. Must NOT contain "[To be verified via MCA]" placeholders.

13. CLOSING: Must end with "Yours faithfully," and "Sd/-" followed by complainant \
    details. The last substantive sentence before the signature should contain \
    "at your risk, cost and consequences, which please note."

OUTPUT:
- Return the COMPLETE refined notice.
- Output ONLY the notice text — no review commentary.
"""


class NoticeDraftAgent:
    """Drafts a legal notice using Claude as the core writer.

    Uses a TWO-PASS pipeline:
    1. DRAFT pass: Full notice generation from the comprehensive brief
    2. REFINE pass: Senior advocate review that tightens specificity,
       removes hallucinated citations, and ensures proportionality
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
        tier: ServiceTier = ServiceTier.self_send,
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

        # ── Select prompt based on tier ───────────────────────────────
        is_self = tier == ServiceTier.self_send
        system_prompt = _SELF_SEND_SYSTEM_PROMPT if is_self else _SYSTEM_PROMPT
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
                "of transaction. Failure to refund within the cure period constitutes continuing deficiency "
                "under §2(11) CPA 2019."
            )
        if "replacement" in facts_combined or "replace" in facts_combined:
            hints.append(
                "REPLACEMENT STRATEGY: Demand replacement within cure period as PRIMARY relief, "
                "with escalation to full refund + compensation if not provided. "
                "Cite §39(1)(b) CPA 2019 (replacement) alongside §39(1)(a) (refund as fallback)."
            )
        if "repair" in facts_combined or "service" in facts_combined:
            hints.append(
                "SERVICE/REPAIR STRATEGY: Frame as deficiency in service under §2(11) CPA 2019. "
                "Demand specific performance within cure period, with monetary compensation for "
                "the period of deprivation."
            )

        # ── Evidence strength calibration ────────────────────────────
        if evidence_score:
            score = evidence_score.overall_score
            if score >= 8:
                hints.append(
                    f"STRONG EVIDENCE (score: {score}/10): The documentary evidence is strong. "
                    "Write with a confident, assertive tone. State that the complainant will "
                    "produce all evidence before the Consumer Commission."
                )
            elif score >= 5:
                hints.append(
                    f"MODERATE EVIDENCE (score: {score}/10): Balance documentary evidence with "
                    "statutory presumptions. Where applicable, note that the burden of proof lies "
                    "on the respondent to disprove unfair trade practice."
                )
            else:
                hints.append(
                    f"LIMITED EVIDENCE (score: {score}/10): Emphasise the respondent's obligation "
                    "to maintain and produce transaction records. Include an evidence preservation "
                    "demand requiring the respondent to retain all records pending adjudication."
                )

            if evidence_score.contradictions:
                hints.append(
                    "CONTRADICTIONS DETECTED: Build argument on the strongest, most consistent "
                    "evidence points only. Do not overclaim on disputed facts."
                )
            if evidence_score.gaps:
                gap_count = len(evidence_score.gaps)
                hints.append(
                    f"EVIDENCE GAPS ({gap_count} found): Add an evidence preservation demand "
                    "requiring respondent to retain all records (call logs, chat transcripts, "
                    "delivery tracking, internal ticket history) pending adjudication."
                )

        elif not complaint.evidence:
            hints.append(
                "NO EVIDENCE LISTED: Include an evidence preservation demand. Note that the "
                "respondent's own records constitute the best evidence and demand their production."
            )

        # ── Timeline strength ────────────────────────────────────────
        timeline_count = len(complaint.timeline)
        if timeline_count >= 5:
            hints.append(
                f"RICH TIMELINE ({timeline_count} events): Weave dates into the facts narrative "
                "to show a pattern of neglect and delay. Use the pre-computed day counts from the brief."
            )
        elif timeline_count >= 2:
            hints.append(
                "MODERATE TIMELINE: Anchor facts on concrete dates. Use the total elapsed days "
                "from the brief to frame the duration as unreasonable."
            )
        elif timeline_count < 2:
            hints.append(
                "SPARSE TIMELINE: Anchor on the transaction date and current date. Use the "
                "pre-computed total days of inaction from the brief."
            )

        # ── T&C defense preparation ────────────────────────────────
        if tc_counter_result and tc_counter_result.counters:
            counter_count = len(tc_counter_result.counters)
            hints.append(
                f"T&C DEFENSES ({counter_count}): Weave the strongest 1-2 counter-arguments into "
                "the Legal Position section naturally. Do not create a separate rebuttal section. "
                "Example: 'Any reliance on your no-refund clause is misplaced, as §2(46) CPA 2019 "
                "renders such unfair contract terms unenforceable.'"
            )

        # ── Arbitration handling ─────────────────────────────────────
        if arbitration_result and arbitration_result.clauses_found:
            hints.append(
                "ARBITRATION CLAUSE DETECTED: Note briefly in the Legal Position that the "
                "arbitration clause does not bar consumer forum jurisdiction, citing Emaar MGF "
                "v. Aftab Singh (2019) 12 SCC 1. Keep it to 1-2 sentences — not a separate section."
            )

        # ── Claim analysis integration ───────────────────────────────
        if claim_results:
            all_pass = all(cr.overall_pass for cr in claim_results)
            partial_count = sum(1 for cr in claim_results if not cr.overall_pass)
            if all_pass:
                hints.append(
                    "ALL CLAIM ELEMENTS SATISFIED: Write with a confident posture. The factual "
                    "and legal position is well-supported on all counts."
                )
            elif partial_count > 0:
                hints.append(
                    f"PARTIAL CLAIMS ({partial_count} with gaps): Lead with the strongest claim "
                    "elements. For partial claims, frame gaps as matters to be established through "
                    "respondent's own records at hearing stage."
                )

        # ── Limitation awareness ─────────────────────────────────────
        if limitation_result:
            warning = limitation_result.warning.lower()
            if "expiring" in warning or "urgent" in warning:
                hints.append(
                    "TIME-SENSITIVE CLAIM: Note that the claim is within the limitation period "
                    "but approaching expiry. Reserve the right to file the complaint without "
                    "awaiting the expiry of the cure period if necessitated by limitation."
                )

        # ── Emotional/harassment component ──────────────────────────
        if "mental agony" in facts_combined or "harassment" in facts_combined or "stress" in facts_combined:
            hints.append(
                "MENTAL AGONY CLAIM: State compensation as proportionate and linked to specific "
                "incidents of inconvenience or harassment described in the facts."
            )

        # ── Escalation power ────────────────────────────────────────
        if escalation_strategy and escalation_strategy.tactics:
            tactic_count = len(escalation_strategy.tactics)
            hints.append(
                f"ESCALATION ({tactic_count} tactics available): In the Consequence section, "
                "include only the 2-3 MOST RELEVANT tactics proportionate to the dispute value. "
                "Do NOT list all tactics. Choose: (1) consumer commission filing, (2) the most "
                "relevant sector-specific regulator, and (3) one additional tactic if appropriate. "
                "A real lawyer's notice does not list 8-10 escalation tactics."
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

        # ── Pre-computed elapsed days (so the LLM does not do date math) ──
        b.append(f"\n## COMPUTED ELAPSED DAYS (use these exact figures — do NOT compute dates yourself)")
        today_date = datetime.utcnow().date()
        date_pattern = re.compile(r'(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})')
        parsed_dates: list[tuple[str, object]] = []
        for event in complaint.timeline:
            dm = date_pattern.search(event)
            if dm:
                try:
                    d, m, y = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
                    if y < 100:
                        y += 2000
                    from datetime import date as _date
                    dt = _date(y, m, d)
                    parsed_dates.append((event[:80], dt))
                except (ValueError, OverflowError):
                    pass
        if parsed_dates:
            first_label, first_dt = parsed_dates[0]
            last_label, last_dt = parsed_dates[-1]
            total_days = (today_date - first_dt).days
            b.append(f"From first event ({first_dt.isoformat()}) to today ({today_date.isoformat()}): {total_days} days")
            if len(parsed_dates) >= 2:
                b.append(f"From first event to last event ({last_dt.isoformat()}): {(last_dt - first_dt).days} days")
                b.append(f"From last event to today: {(today_date - last_dt).days} days")
            for i in range(1, len(parsed_dates)):
                prev_label, prev_dt = parsed_dates[i - 1]
                cur_label, cur_dt = parsed_dates[i]
                gap = (cur_dt - prev_dt).days
                b.append(f"Between '{prev_label}' and '{cur_label}': {gap} days")
        else:
            b.append("No parseable dates found in timeline — state elapsed time in general terms")

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
        b.append(f"\n## STATUTORY PROVISIONS ATTRACTED (cite the 3-5 strongest in the notice)")
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

        # ── T&C Counter-arguments ────────────────────────────────────
        real_counters = [
            c for c in (tc_counter_result.counters if tc_counter_result else [])
            if c.clause_excerpt and c.clause_excerpt.strip()
               and "login page" not in c.clause_excerpt.lower()
               and "navigation" not in c.clause_excerpt.lower()
               and "unavailable" not in c.defense_clause.lower()
        ]
        if real_counters:
            b.append(f"\n## T&C COUNTER-ARGUMENTS (weave the strongest 1-2 into Legal Position)")
            for counter in real_counters:
                b.append(f"\nDefense: {counter.defense_clause}")
                b.append(f"Their clause: \"{counter.clause_excerpt}\"")
                b.append(f"Counter-argument: {counter.legal_counter}")
                b.append(f"Statutory basis: {counter.statutory_basis}")
                if counter.precedent_note:
                    b.append(f"Precedent: {counter.precedent_note}")
        # If no real T&C clauses found, skip this section entirely —
        # do NOT instruct the LLM to fabricate defenses to argue against.

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
            b.append(f"\n## ESCALATION / PRESSURE TACTICS (for Consequence section — pick 2-3 most relevant)")
            b.append(f"Severity level: {escalation_strategy.severity_level}")
            for i, tactic in enumerate(escalation_strategy.tactics, 1):
                b.append(f"\n### Tactic {i}: {tactic.tactic}")
                b.append(f"Action: {tactic.action}")
                b.append(f"Target: {tactic.target_authority}")
                b.append(f"Legal basis: {tactic.legal_basis}")
            b.append(
                "\nINSTRUCTION: In the Consequence of Non-compliance section, include ONLY the "
                "2-3 most relevant tactics proportionate to the dispute value. Always include "
                "the consumer commission filing. Then pick 1-2 sector-specific or regulatory "
                "tactics. Do NOT list all tactics — a real lawyer's notice has a brief, measured "
                "consequence paragraph, not a multi-page escalation manifesto."
            )

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
