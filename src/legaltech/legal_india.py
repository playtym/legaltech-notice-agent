from dataclasses import dataclass


@dataclass(frozen=True)
class LawSection:
    act: str
    section: str
    title: str
    trigger_keywords: tuple[str, ...]
    why_relevant: str
    legacy_reference: str | None = None


INDIA_LAW_SECTIONS: tuple[LawSection, ...] = (
    # ── Consumer Protection Act, 2019 ────────────────────────────────
    LawSection(
        act="Consumer Protection Act, 2019",
        section="Section 2(47)",
        title="Unfair Trade Practice",
        trigger_keywords=("false promise", "misleading", "ad", "hidden charge", "unfair", "dark pattern"),
        why_relevant="Covers misleading statements and unfair methods in selling goods/services.",
    ),
    LawSection(
        act="Consumer Protection Act, 2019",
        section="Section 2(11)",
        title="Deficiency in Service",
        trigger_keywords=("service", "delay", "not delivered", "support ignored", "deficiency"),
        why_relevant="Useful when service quality/performance is below what was promised.",
    ),
    LawSection(
        act="Consumer Protection Act, 2019",
        section="Section 35",
        title="Manner to file complaint",
        trigger_keywords=("complaint", "district commission", "consumer forum", "file claim"),
        why_relevant="Framework section to indicate readiness for formal consumer complaint.",
    ),
    LawSection(
        act="Consumer Protection Act, 2019",
        section="Section 59",
        title="Product liability",
        trigger_keywords=("defective", "manufacturing defect", "product liability", "faulty product", "dangerous product", "injury"),
        why_relevant="Imposes strict liability on manufacturer/seller for defective products causing harm.",
    ),
    LawSection(
        act="Consumer Protection Act, 2019",
        section="Section 62",
        title="Punitive damages for unfair trade practice",
        trigger_keywords=("punitive", "repeated offence", "willful", "deliberate", "gross negligence"),
        why_relevant="Allows punitive damages where respondent's conduct is willfully unfair or grossly negligent.",
    ),
    # ── Indian Contract Act, 1872 ────────────────────────────────────
    LawSection(
        act="Indian Contract Act, 1872",
        section="Section 73",
        title="Compensation for loss from breach",
        trigger_keywords=("breach", "contract", "loss", "damages", "refund refused"),
        why_relevant="Supports claim for foreseeable losses caused by breach of contract.",
    ),
    # ── Specific Relief Act, 1963 ────────────────────────────────────
    LawSection(
        act="Specific Relief Act, 1963",
        section="Section 14",
        title="Specific performance of contract",
        trigger_keywords=("replace", "restore", "specific performance", "complete the work", "deliver"),
        why_relevant="Seek specific performance (replacement/restoration) when damages alone are inadequate.",
    ),
    # ── Information Technology Act, 2000 ─────────────────────────────
    LawSection(
        act="Information Technology Act, 2000",
        section="Section 43A",
        title="Compensation for failure to protect data",
        trigger_keywords=("data leak", "privacy", "security", "personal data"),
        why_relevant="Compensation for negligent data handling causing wrongful loss.",
    ),
    # ── Digital Personal Data Protection Act, 2023 ───────────────────
    LawSection(
        act="Digital Personal Data Protection Act, 2023",
        section="Section 8 read with Section 13",
        title="Obligations of data fiduciary",
        trigger_keywords=("consent", "data processing", "personal data", "privacy policy", "data fiduciary"),
        why_relevant="Imposes obligations on entities processing personal data; breach entitles consumer to compensation via Data Protection Board.",
    ),
    # ── E-Commerce Rules, 2020 ───────────────────────────────────────
    LawSection(
        act="Consumer Protection (E-Commerce) Rules, 2020",
        section="Rules 4, 5, 6",
        title="E-commerce entity obligations",
        trigger_keywords=("marketplace", "e-commerce", "online order", "platform", "seller on", "flipkart", "amazon", "meesho"),
        why_relevant="Mandates sellers and marketplaces to display accurate info, process grievances in 1 month, and provide refunds per stated policy.",
    ),
    # ── Payment and Settlement Systems Act, 2007 ─────────────────────
    LawSection(
        act="Payment and Settlement Systems Act, 2007",
        section="Section 18 read with RBI directions",
        title="Payment system compliance",
        trigger_keywords=("wallet", "upi", "payment failed", "unauthorized transaction", "banking ombudsman"),
        why_relevant="Use for payment failures or unauthorized transactions with regulated entities. Escalate via RBI Integrated Ombudsman after 30 days.",
    ),
    # ── Sale of Goods Act, 1930 ──────────────────────────────────────
    LawSection(
        act="Sale of Goods Act, 1930",
        section="Section 16",
        title="Implied conditions as to quality or fitness",
        trigger_keywords=("not fit", "poor quality", "unfit for purpose", "merchantable quality", "warranty"),
        why_relevant="Implied condition that goods are of merchantable quality and fit for purpose.",
    ),
    # ══════════════════════════════════════════════════════════════════
    # DARK PATTERNS (P0)
    # ══════════════════════════════════════════════════════════════════
    LawSection(
        act="Guidelines for Prevention and Regulation of Dark Patterns, 2023 (notified under CPA 2019)",
        section="Guidelines 3-4 read with Schedule",
        title="Prohibition of dark patterns",
        trigger_keywords=(
            "dark pattern", "false urgency", "basket sneaking", "confirm shaming",
            "forced action", "subscription trap", "interface interference",
            "bait and switch", "hidden cost", "nagging", "trick question",
            "disguised ad", "saas roaming",
        ),
        why_relevant=(
            "CCPA Dark Pattern Guidelines 2023 identify 13 specific dark patterns as unfair trade "
            "practices under CPA 2019 §2(47). Penalty up to ₹50 lakh (first offence) / ₹10 lakh "
            "per subsequent offence for the platform."
        ),
    ),
    LawSection(
        act="Consumer Protection Act, 2019",
        section="Sections 18-27",
        title="CCPA powers — investigation, recall, and penalty",
        trigger_keywords=(
            "ccpa", "central consumer protection authority", "product recall",
            "misleading advertisement", "false advertisement", "penalty",
        ),
        why_relevant=(
            "CCPA can suo motu or on complaint investigate unfair trade practices, order product "
            "recall, impose penalty up to ₹10 lakh on endorser and ₹50 lakh on manufacturer/trader."
        ),
    ),
    # ══════════════════════════════════════════════════════════════════
    # UPI / PAYMENT FAILURES (P0)
    # ══════════════════════════════════════════════════════════════════
    LawSection(
        act="RBI Circular on Harmonisation of TAT for Resolution of Failed Transactions (2019)",
        section="RBI/DPSS/2019-20/174 read with RBI/2022-23/151",
        title="Auto-reversal of failed UPI/IMPS/wallet transactions",
        trigger_keywords=(
            "upi failed", "upi deducted", "payment failed", "money deducted",
            "double debit", "auto reversal", "t+5", "failed transaction",
            "amount deducted but not credited", "transaction failed",
        ),
        why_relevant=(
            "RBI mandates auto-reversal within T+5 business days for UPI/IMPS failures. "
            "Bank must pay ₹100/day compensation for delay beyond TAT. Non-compliance "
            "reportable to RBI Ombudsman."
        ),
    ),
    LawSection(
        act="RBI Master Direction on Digital Payment Security Controls (2021)",
        section="RBI/2020-21/84 DOC.CO.DPSS.CC.No.S-516/02.01.011/2020-21",
        title="Zero-liability for unauthorized electronic transactions",
        trigger_keywords=(
            "unauthorized transaction", "fraud", "hacked", "stolen",
            "zero liability", "unauthorized debit", "phishing",
            "sim swap", "account hacked",
        ),
        why_relevant=(
            "RBI mandates zero customer liability if reported within 3 working days. "
            "Customer liability capped at ₹10,000 if reported within 4-7 days. "
            "Bank bears full liability for third-party breach."
        ),
    ),
    LawSection(
        act="RBI Integrated Ombudsman Scheme, 2021",
        section="Scheme Clauses 8-10",
        title="RBI Ombudsman for banking/payment complaints",
        trigger_keywords=(
            "banking ombudsman", "rbi ombudsman", "rbi complaint",
            "cms.rbi.org.in", "integrated ombudsman",
        ),
        why_relevant=(
            "Unified ombudsman scheme covering banks, NBFCs, and payment system operators. "
            "Free, no lawyer needed. Must file within 1 year of final reply / 30 days of no reply."
        ),
    ),
    # ══════════════════════════════════════════════════════════════════
    # ED-TECH REFUNDS (P0)
    # ══════════════════════════════════════════════════════════════════
    LawSection(
        act="Consumer Protection Act, 2019",
        section="Section 2(47) read with Section 2(28)",
        title="Unfair trade practice — misleading advertisements in education",
        trigger_keywords=(
            "edtech", "ed-tech", "byju", "unacademy", "upgrad", "whitehat",
            "coaching", "course refund", "placement guarantee", "job guarantee",
            "skill course", "online course", "learning app",
        ),
        why_relevant=(
            "Education is a 'service' under CPA 2019. False placement guarantees, "
            "misleading course descriptions, and aggressive sales tactics constitute "
            "unfair trade practice. CCPA has issued specific orders against ed-tech firms."
        ),
    ),
    LawSection(
        act="UGC (Refund of Fees) Guidelines, 2023",
        section="UGC Guidelines read with AICTE Process Handbook",
        title="Fee refund policy for higher education and ed-tech",
        trigger_keywords=(
            "fee refund", "admission cancel", "withdrawal", "cooling off",
            "ugc refund", "aicte refund", "semester fee",
        ),
        why_relevant=(
            "UGC mandates full refund (minus processing fee) if withdrawal before course start. "
            "Even after start, proportionate refund is mandated. Ed-tech platforms offering "
            "UGC/AICTE-affiliated courses must comply."
        ),
    ),
    # ══════════════════════════════════════════════════════════════════
    # AIRLINE COMPENSATION (P1)
    # ══════════════════════════════════════════════════════════════════
    LawSection(
        act="DGCA Civil Aviation Requirement (CAR) Section 3, Series M, Part IV",
        section="CAR Issue III, Rev 1 (2022)",
        title="Passenger entitlements — denial of boarding, cancellation, delay",
        trigger_keywords=(
            "flight cancel", "flight delay", "denied boarding", "overbooked",
            "missed flight", "airline compensation", "dgca", "air sewa",
            "indigo", "air india", "spicejet", "vistara", "akasa",
            "lost baggage", "damaged baggage",
        ),
        why_relevant=(
            "DGCA CAR mandates: (a) denied boarding — 200-400% of fare, (b) cancellation <24h notice "
            "— up to ₹20,000 compensation + alternate flight/refund, (c) delay >2h — meals, >6h — "
            "hotel + ₹20,000, (d) tarmac delay >3h — right to deplane. Airline must inform rights proactively."
        ),
    ),
    LawSection(
        act="Carriage by Air Act, 1972 (incorporating Montreal Convention)",
        section="Section 5 read with Montreal Convention Articles 17-22",
        title="International air carriage — baggage/delay compensation",
        trigger_keywords=(
            "international flight", "lost luggage", "baggage delay",
            "montreal convention", "carriage by air", "sdr",
        ),
        why_relevant=(
            "For international routes: airline strictly liable for baggage loss/damage up to 1,288 SDR "
            "(~₹1.4 lakh), delay compensation up to 5,346 SDR (~₹5.8 lakh). No need to prove negligence."
        ),
    ),
    # ══════════════════════════════════════════════════════════════════
    # RERA — REAL ESTATE DELAY (P1)
    # ══════════════════════════════════════════════════════════════════
    LawSection(
        act="Real Estate (Regulation and Development) Act, 2016",
        section="Section 18",
        title="Delay compensation — interest or withdrawal with refund",
        trigger_keywords=(
            "rera", "delayed possession", "builder delay", "possession date",
            "agreement date", "flat delay", "apartment delay",
            "construction delay", "real estate delay",
        ),
        why_relevant=(
            "If builder fails to deliver by agreement date, buyer has two choices: "
            "(1) withdraw + full refund + interest at SBI MCLR + 2%, or "
            "(2) continue + interest for every month of delay at same rate. "
            "Interest runs from promised date to actual possession."
        ),
    ),
    LawSection(
        act="Real Estate (Regulation and Development) Act, 2016",
        section="Sections 14, 19(3), 19(4)",
        title="Adherence to sanctioned plans and structural defect warranty",
        trigger_keywords=(
            "specification change", "layout change", "structural defect",
            "construction quality", "wrong specification", "different from brochure",
            "carpet area", "super area",
        ),
        why_relevant=(
            "Builder cannot alter sanctioned plans without 2/3 allottee consent (§14). "
            "5-year structural defect warranty from possession (§14(3)). "
            "Carpet area must match agreement (§19(3))."
        ),
    ),
    # ══════════════════════════════════════════════════════════════════
    # INSURANCE CLAIM REJECTION (P1)
    # ══════════════════════════════════════════════════════════════════
    LawSection(
        act="IRDAI (Protection of Policyholders' Interests) Regulations, 2017",
        section="Regulation 17(6) and 17(7)",
        title="Mandatory claim settlement timeline and reasons for rejection",
        trigger_keywords=(
            "claim rejected", "claim denied", "claim repudiated",
            "insurance rejected", "insurance denied", "tpa rejected",
            "cashless denied", "claim settled less", "partial settlement",
        ),
        why_relevant=(
            "Insurer MUST settle within 30 days of last document or reject with SPECIFIC reasons "
            "in writing (Reg 17(7)). Delay beyond 30 days attracts interest at bank rate + 2%. "
            "Vague rejection ('not covered') is itself a regulatory violation."
        ),
    ),
    LawSection(
        act="Insurance Act, 1938",
        section="Section 45",
        title="Two-year contestability clause",
        trigger_keywords=(
            "policy cancelled", "misrepresentation", "non-disclosure",
            "pre-existing disease", "contestability", "policy void",
        ),
        why_relevant=(
            "After 2 years from policy inception, insurer CANNOT repudiate on grounds of "
            "misstatement or non-disclosure, unless fraud is proven. This is an absolute bar."
        ),
    ),
    # ══════════════════════════════════════════════════════════════════
    # CREDIT SCORE DISPUTES (P2)
    # ══════════════════════════════════════════════════════════════════
    LawSection(
        act="Credit Information Companies (Regulation) Act, 2005",
        section="Section 15 read with RBI Circular on Credit Information",
        title="Right to dispute and correct credit information",
        trigger_keywords=(
            "credit score", "cibil", "cibil score", "credit report",
            "wrong credit", "default wrongly", "experian", "equifax",
            "crif", "credit information",
        ),
        why_relevant=(
            "Consumer can dispute inaccurate credit data. CIC must resolve within 30 days "
            "(§15). Credit institution must rectify or confirm within 21 days. Wrong reporting "
            "constitutes deficiency in service under CPA 2019."
        ),
    ),
    # ══════════════════════════════════════════════════════════════════
    # QUICK COMMERCE / EXPIRED FOOD (P2)
    # ══════════════════════════════════════════════════════════════════
    LawSection(
        act="Food Safety and Standards Act, 2006",
        section="Sections 26, 27 read with Sections 50-59",
        title="Food business operator obligations and penalties for unsafe food",
        trigger_keywords=(
            "expired food", "stale food", "contaminated food", "food poisoning",
            "rotten", "spoiled", "mouldy", "insect in food", "foreign object",
            "blinkit", "zepto", "instamart", "swiggy instamart", "bigbasket",
            "quick commerce", "instant delivery",
        ),
        why_relevant=(
            "FBO must ensure food is not unsafe/sub-standard (§26). Selling article beyond "
            "expiry date is punishable with imprisonment up to 6 months + fine up to ₹5 lakh (§59). "
            "Quick commerce platforms are FBOs and must hold FSSAI license for storage/delivery."
        ),
    ),
    LawSection(
        act="Food Safety and Standards (Labelling and Display) Regulations, 2020",
        section="Regulation 5",
        title="Mandatory labelling — expiry date, FSSAI license, ingredients",
        trigger_keywords=(
            "no expiry date", "expiry not visible", "fssai number missing",
            "label missing", "mislabelled", "wrong mrp",
        ),
        why_relevant=(
            "Every packaged food must display manufacture date, best before/use by date, "
            "FSSAI license number, and ingredient list. Non-compliance is punishable under FSSA §52."
        ),
    ),
)


def match_law_sections(issue_text: str) -> list[LawSection]:
    text = issue_text.lower()
    matches: list[LawSection] = []
    for section in INDIA_LAW_SECTIONS:
        if any(keyword in text for keyword in section.trigger_keywords):
            matches.append(section)
    return matches
