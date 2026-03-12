"""Authoritative legal retrieval service.

Provides curated bare-act text, latest amendments, and state-level rules
for sections cited by the legal analysis agent. In production, back this
with a vector store or a legal-database API (e.g. Indian Kanoon, SCC Online).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BareActEntry:
    act: str
    section: str
    title: str
    bare_text: str
    amendment_note: str | None = None
    state_rules: list[str] = field(default_factory=list)


# ── Curated bare-act excerpts (civil-only, consumer-facing) ──────────────

_BARE_ACT_DB: dict[str, BareActEntry] = {
    "CPA-2019-2(47)": BareActEntry(
        act="Consumer Protection Act, 2019",
        section="Section 2(47)",
        title="Unfair Trade Practice",
        bare_text=(
            '"unfair trade practice" means a trade practice which, for the purpose of promoting '
            "the sale, use or supply of any goods or for the provision of any service, adopts any "
            "unfair method or unfair or deceptive practice including false representation, "
            "misleading advertisement, or offering gifts/prizes with the intention to not provide them."
        ),
        amendment_note="No amendment since enactment (2019). Replaces CPA 1986 §2(1)(r).",
    ),
    "CPA-2019-2(11)": BareActEntry(
        act="Consumer Protection Act, 2019",
        section="Section 2(11)",
        title="Deficiency",
        bare_text=(
            '"deficiency" means any fault, imperfection, shortcoming or inadequacy in the quality, '
            "nature and manner of performance which is required to be maintained by or under any law "
            "for the time being in force or has been undertaken to be performed by a person in "
            "pursuance of a contract or otherwise in relation to any service."
        ),
        amendment_note="No amendment since enactment (2019). Replaces CPA 1986 §2(1)(g).",
    ),
    "CPA-2019-35": BareActEntry(
        act="Consumer Protection Act, 2019",
        section="Section 35",
        title="Jurisdiction of District Commission & manner of complaint",
        bare_text=(
            "A consumer complaint may be filed before the District Commission within whose "
            "jurisdiction the opposite party resides or carries on business or where the cause of "
            "action arose. The complaint shall be in writing and accompanied by such fee as may be "
            "prescribed."
        ),
        amendment_note=(
            "Consumer Protection (Consumer Commission Procedure) Regulations, 2020 prescribe fees and "
            "e-filing. Check state amendments for local fee schedules."
        ),
        state_rules=[
            "Maharashtra: Maharashtra State Consumer Disputes Redressal Commission Rules, 2020",
            "Karnataka: Karnataka State Consumer Disputes Redressal Commission Rules, 2021",
            "Delhi: Delhi State Consumer Disputes Redressal Commission Rules, 2020",
        ],
    ),
    "ICA-1872-73": BareActEntry(
        act="Indian Contract Act, 1872",
        section="Section 73",
        title="Compensation for loss or damage caused by breach of contract",
        bare_text=(
            "When a contract has been broken, the party who suffers by such breach is entitled to "
            "receive, as compensation for any loss or damage caused to him thereby, such compensation "
            "as naturally arose in the usual course of things from such breach, or which the parties "
            "knew, when they made the contract, to be likely to result from the breach of it."
        ),
        amendment_note="Unamended since 1872. Settled interpretation per Hadley v. Baxendale principle.",
    ),
    "ITA-2000-43A": BareActEntry(
        act="Information Technology Act, 2000",
        section="Section 43A",
        title="Compensation for failure to protect data",
        bare_text=(
            "Where a body corporate, possessing, dealing or handling any sensitive personal data or "
            "information in a computer resource which it owns, controls or operates, is negligent in "
            "implementing and maintaining reasonable security practices, and thereby causes wrongful "
            "loss or wrongful gain to any person, such body corporate shall be liable to pay damages "
            "by way of compensation to the person so affected."
        ),
        amendment_note=(
            "IT (Reasonable Security Practices and Procedures) Rules, 2011 apply. "
            "Digital Personal Data Protection Act, 2023 §33/44 may supersede for consent-based claims once notified."
        ),
    ),
    "PSS-2007-18": BareActEntry(
        act="Payment and Settlement Systems Act, 2007",
        section="Section 18 read with RBI Directions",
        title="Payment system compliance and grievance redressal",
        bare_text=(
            "The Reserve Bank may, in public interest, give such directions to any payment system or "
            "system participant as it may consider necessary. Read with RBI Integrated Ombudsman "
            "Scheme, 2021 for consumer grievance escalation after 30 days of unresolved complaint."
        ),
        amendment_note="RBI Integrated Ombudsman Scheme, 2021 replaced earlier banking/NBFC ombudsman schemes.",
    ),
    "CPA-2019-59": BareActEntry(
        act="Consumer Protection Act, 2019",
        section="Section 59",
        title="Liability of product manufacturer",
        bare_text=(
            "A product manufacturer shall be liable in a product liability action if the product "
            "contains a manufacturing defect, is defective in design, or there is a deviation from "
            "manufacturing specifications, or the product does not conform to the express warranty."
        ),
        amendment_note="No amendment since enactment (2019). New provision — no equivalent in CPA 1986.",
    ),
    "CPA-2019-62": BareActEntry(
        act="Consumer Protection Act, 2019",
        section="Section 62",
        title="Exceptions to product liability action",
        bare_text=(
            "A product liability action cannot be brought against the product seller if the product "
            "was not substantially altered by the seller and the seller did not exercise substantial "
            "control over the designing, testing, manufacturing, packaging or labelling of the product."
        ),
        amendment_note=(
            "No amendment since enactment (2019). Used with §59/§60/§84 to assess product liability chain. "
            "Read with CPA 2019 §86 for punitive damages provisions."
        ),
    ),
    "DPDP-2023-8": BareActEntry(
        act="Digital Personal Data Protection Act, 2023",
        section="Sections 8 and 13",
        title="Obligations of Data Fiduciary / Breach notification",
        bare_text=(
            "§8: A Data Fiduciary shall process personal data only for lawful purposes for which "
            "consent was given. §13: In the event of a personal data breach, the Data Fiduciary shall "
            "notify the Board and each affected Data Principal in the prescribed manner."
        ),
        amendment_note=(
            "Enacted August 2023. Rules under DPDP Act not yet fully notified as of 2024. "
            "Penalty up to ₹250 crore per §33. Supersedes IT Act §43A for consent-based data claims once rules notified."
        ),
    ),
    "ECOM-2020-R4-6": BareActEntry(
        act="Consumer Protection (E-Commerce) Rules, 2020",
        section="Rules 4, 5 and 6",
        title="E-Commerce duties: entity info, pricing transparency, grievance redressal",
        bare_text=(
            "Rule 4: Every e-commerce entity shall provide information about legal name, principal "
            "geographic address, website, customer care number, and grievance officer details. "
            "Rule 5: Sellers shall not manipulate price to gain unreasonable profit, or discriminate "
            "between consumers of same class. Rule 6: No e-commerce entity shall impose cancellation "
            "charges unless similar charges are borne by the entity itself."
        ),
        amendment_note=(
            "Notified 23 July 2020 under CPA 2019 §101. Amendments proposed in 2021 draft "
            "(flash sales ban, fall back liability) not yet notified."
        ),
    ),
    "SRA-1963-14": BareActEntry(
        act="Specific Relief Act, 1963",
        section="Section 14",
        title="Contracts not specifically enforceable",
        bare_text=(
            "The following contracts cannot be specifically enforced: (a) where a party has obtained "
            "substituted performance under Section 20; (b) a contract the performance of which "
            "involves the performance of a continuous duty which the court cannot supervise; "
            "(c) a contract so dependent on the personal qualifications of the parties that the court "
            "cannot enforce specific performance of its material terms."
        ),
        amendment_note=(
            "Amended 2018 (Specific Relief (Amendment) Act, 2018): Substituted performance (§20) "
            "introduced. §14 narrowed — specific performance is now the rule, not the exception."
        ),
    ),
    "SOGA-1930-16": BareActEntry(
        act="Sale of Goods Act, 1930",
        section="Section 16",
        title="Implied condition as to quality or fitness",
        bare_text=(
            "Where the buyer, expressly or by implication, makes known to the seller the particular "
            "purpose for which the goods are required, so as to show that the buyer relies on the "
            "seller's skill or judgment, there is an implied condition that the goods shall be "
            "reasonably fit for such purpose."
        ),
        amendment_note="Unamended since 1930. Foundational implied warranty provision for product quality claims.",
    ),
}

# ── Key mapping: act-section → DB key ────────────────────────────────────

_SECTION_KEY_MAP: dict[str, str] = {
    "Section 2(47)": "CPA-2019-2(47)",
    "Section 2(11)": "CPA-2019-2(11)",
    "Section 35": "CPA-2019-35",
    "Section 59": "CPA-2019-59",
    "Section 62": "CPA-2019-62",
    "Section 73": "ICA-1872-73",
    "Section 43A": "ITA-2000-43A",
    "Section 18 read with RBI directions": "PSS-2007-18",
    "Sections 8 and 13": "DPDP-2023-8",
    "Rules 4, 5 and 6": "ECOM-2020-R4-6",
    "Section 14": "SRA-1963-14",
    "Section 16": "SOGA-1930-16",
}


def lookup_bare_act(section_id: str) -> BareActEntry | None:
    key = _SECTION_KEY_MAP.get(section_id)
    if key:
        return _BARE_ACT_DB.get(key)
    return None


def lookup_all_matched(section_ids: list[str]) -> list[BareActEntry]:
    results: list[BareActEntry] = []
    for sid in section_ids:
        entry = lookup_bare_act(sid)
        if entry:
            results.append(entry)
    return results
