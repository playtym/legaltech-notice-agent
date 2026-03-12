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
)


def match_law_sections(issue_text: str) -> list[LawSection]:
    text = issue_text.lower()
    matches: list[LawSection] = []
    for section in INDIA_LAW_SECTIONS:
        if any(keyword in text for keyword in section.trigger_keywords):
            matches.append(section)
    return matches
