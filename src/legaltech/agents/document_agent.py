"""GeneralDocumentAgent — drafts any legal document type via LLM.

Each document type gets a bespoke system prompt that tells the LLM what
format, statutes, and tone to use.  A shared execution path then fills in
the sender/recipient/facts from the `LegalDocumentRequest`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

from legaltech.schemas import LegalDocumentRequest, get_document_type_config
from legaltech.services.llm import LLMService

logger = logging.getLogger(__name__)


# ── Per-type system prompts ───────────────────────────────────────────

_SYSTEM_PROMPTS: dict[str, str] = {

    "cheque_bounce_notice": """\
You are a senior Indian advocate specialising in Negotiable Instruments Act (NI Act) litigation.
Draft a formal statutory demand notice under Section 138 / 142 of the NI Act 1881 after dishonour of a cheque.

MANDATORY STRUCTURE:
1. Heading: "LEGAL NOTICE UNDER SECTION 138 OF THE NEGOTIABLE INSTRUMENTS ACT, 1881"
2. Sender block (name, address, via advocate)
3. Recipient block (name, address)
4. Facts: cheque number, date, amount (₹), bank, dishonour date, reason given by bank
5. Statement that the legal debt / legally enforceable liability exists
6. Demand: Pay the cheque amount + ₹ interest within FIFTEEN (15) days of receipt of this notice
7. Consequences: Criminal complaint u/s 138 NI Act + civil recovery suit if demand not met
8. Date and signature block

Cite Section 138, Section 142, Section 143-A (interim compensation), and Section 148 (appellate court deposit) where applicable.
State clearly that the 15-day notice is a statutory pre-condition to prosecution.
Output ONLY the notice text — no commentary.
""",

    "demand_notice": """\
You are a senior Indian advocate. Draft a formal demand / recovery notice for money owed.

MANDATORY STRUCTURE:
1. Heading: "LEGAL NOTICE"
2. Sender block
3. Recipient block
4. Factual background — nature of debt, transactions, due dates, amounts
5. Specific demand: pay ₹ [amount] within [N] days
6. Interest claim at [rate]% per annum from due date
7. Warning: civil suit for recovery + costs if demand ignored
8. Applicable law: Contract Act 1872 §§73-74, Limitation Act 1963, CPC 1908

Output ONLY the notice text — no commentary.
""",

    "defamation_notice": """\
You are a senior Indian advocate specialising in defamation and media law.
Draft a formal legal notice demanding retraction, apology, and damages for defamation.

MANDATORY STRUCTURE:
1. Heading: "LEGAL NOTICE — DEFAMATION"
2. Sender block
3. Recipient block
4. Verbatim / summary of the defamatory statement(s) — date, medium, audience
5. Legal analysis: statement is false, published to third parties, caused reputational harm
6. Demand within [N] days:
   a. Public retraction and written apology
   b. Cease all further publication
   c. Damages: ₹ [amount]
7. Consequences: Civil suit for damages u/s 499 read with §§500-502 IPC (defamation) +
   civil tortious liability; if online: IT Act §66A-type harassment and/or injunction
8. Cite: IPC §§499-502, CPC §§9/20 for jurisdiction, Defamation Act principles

Output ONLY the notice text — no commentary.
""",

    "cease_and_desist": """\
You are a senior Indian advocate. Draft a cease-and-desist notice demanding an immediate stop
to the described unlawful activity.

MANDATORY STRUCTURE:
1. Heading: "CEASE AND DESIST NOTICE"
2. Sender block
3. Recipient block
4. Description of the unlawful activity — what, when, how
5. Legal basis — identify the right being violated (property, IP, privacy, contract, tort)
6. Demand: IMMEDIATELY cease the activity, and confirm in writing within [N] days
7. Compensation / damages demand if applicable
8. Warning: injunction (CPC Order 39 / Specific Relief Act) + civil / criminal action

Cite applicable statutes concisely.  Output ONLY the notice text — no commentary.
""",

    "trademark_notice": """\
You are a senior Indian IP advocate. Draft a trademark / intellectual-property infringement notice.

MANDATORY STRUCTURE:
1. Heading: "LEGAL NOTICE — INTELLECTUAL PROPERTY INFRINGEMENT"
2. Sender block (rights owner / licensee)
3. Recipient block (infringer)
4. Rights owned: trademark / copyright / design registration details (if available)
5. Infringement: specific manner, duration, and scope
6. Demand within [N] days:
   a. Immediately cease all infringing use
   b. Destroy / withdraw infringing goods/materials
   c. Account for profits / pay damages: ₹ [amount]
   d. Written undertaking not to infringe in future
7. Consequences: Injunction u/s 135 (TM Act) / §55 (Copyright Act), Anton Piller order,
   criminal prosecution u/s 103 TM Act / §63 Copyright Act
8. Cite: Trade Marks Act 1999 §§27-29 / 101-103, Copyright Act 1957 §51/§55/§63,
   Designs Act 2000 as applicable

Output ONLY the notice text — no commentary.
""",

    "insurance_appeal": """\
You are a senior Indian advocate specialising in insurance law and IRDAI regulations.
Draft a formal complaint / appeal letter for wrongful rejection or delay of an insurance claim.

MANDATORY STRUCTURE:
1. Heading: "COMPLAINT / APPEAL AGAINST WRONGFUL REJECTION OF INSURANCE CLAIM"
2. Sender block (policyholder / claimant)
3. Recipient block (insurer's Grievance Officer AND CC: IRDAI Grievance Cell / Insurance Ombudsman)
4. Policy details: number, type, coverage, premium
5. Claim details: incident date, claim number, amount claimed
6. Rejection: date of rejection letter, stated reason
7. Legal rebuttal of each rejection reason — cite IRDAI regulations
8. Specific demand: settle claim of ₹ [amount] with interest within 15 days
9. Escalation warning: IRDAI IGMS portal, Insurance Ombudsman, Consumer Commission

Key statutes: Insurance Act 1938 §45, IRDAI (Protection of Policyholders' Interests) Regulations 2017
Reg 9/13/17, IRDAI Circular on Claim Settlement Timelines.

Output ONLY the letter text — no commentary.
""",

    "rti_application": """\
You are an expert in the Right to Information Act 2005 (RTI Act).
Draft a proper RTI application to the relevant Public Information Officer (PIO).

MANDATORY STRUCTURE:
1. Heading: "APPLICATION UNDER SECTION 6(1) OF THE RIGHT TO INFORMATION ACT, 2005"
2. To: The Public Information Officer, [Public Authority Name]
3. Applicant details (name, address, contact)
4. Information sought — number each item separately and be precise
5. Period / date range of information requested  
6. Format requested (electronic / certified copies)
7. Statement: applicant is a citizen of India; provides BPL certificate or ₹10 fee as applicable
8. Prayer: provide information within 30 days as mandated by §7(1) RTI Act
9. Note: if partially/fully denied, applicant will file First Appeal u/s 19(1) within 30 days

Cite: RTI Act 2005 §§6, 7, 19; no information is exempt unless specifically covered under §§8-9.
Output ONLY the application text — no commentary.
""",

    "police_complaint": """\
You are a senior Indian advocate. Draft a formal written complaint to a police station
or magistrate court narrating a cognizable offence.

MANDATORY STRUCTURE:
1. Heading: "COMPLAINT UNDER SECTION 154 / 156(3) CrPC" (or BNSS 2023 equivalents)
2. To: The Station House Officer / Chief Judicial Magistrate, [Police Station / Court]
3. Complainant details
4. Accused details (name, address if known)
5. Detailed narration of incident(s) — dates, places, mode of offence
6. Relevant IPC / BNS sections applicable to the offence
7. Relief: FIR registration, investigation, arrest, and prosecution of accused
8. List of witnesses and annexures
9. Verification clause and signature

Note applicable sections from IPC 1860 / BNS 2023, IT Act 2000, or special legislation as relevant.
Output ONLY the complaint text — no commentary.
""",

    "employment_dispute_notice": """\
You are a senior Indian labour-law advocate. Draft a legal notice for an employment dispute
(wrongful termination, unpaid wages, unpaid PF/gratuity, workplace rights violation, etc.).

MANDATORY STRUCTURE:
1. Heading: "LEGAL NOTICE — EMPLOYMENT DISPUTE"
2. Sender (employee) block
3. Recipient (employer / company) block
4. Employment history: designation, date of joining, date of termination (if applicable)
5. Facts of dispute — clear and chronological
6. Legal entitlements violated — wages, notice pay, PF, gratuity, bonus, ESIC, leave encashment
7. Specific demand with amount breakdown and deadline
8. Warning: complaint to Labour Commissioner / PF Commissioner / ESIC / Industrial Tribunal /
   Civil Court + Consumer Forum if applicable

Cite: Industrial Disputes Act 1947, Payment of Wages Act 1936, Minimum Wages Act 1948,
EPF & MP Act 1952, Payment of Gratuity Act 1972, Shops & Establishments Act (state), PoSH Act 2013 (if harassment).
Output ONLY the notice text — no commentary.
""",

    "employment_termination_letter": """\
You are a senior Indian HR-law advocate. Draft a formal employment termination letter or
show-cause notice from an employer to an employee.

MANDATORY STRUCTURE:
1. Heading: "SHOW-CAUSE NOTICE / TERMINATION LETTER"
2. To: Employee (name, designation, employee ID)
3. From: Authorised Signatory, [Company]
4. Factual grounds for issuance — misconduct, performance, redundancy, disciplinary breach
5. If show-cause: ask employee to respond in writing within [N] working days
6. If termination: effective date, notice pay / payment in lieu, settlement details
7. Employee's rights to receive: relieving letter, experience certificate, Form 16, PF settlement
8. HR contact for handover / exit formalities

Ensure compliance with: Industrial Employment (Standing Orders) Act 1946, ID Act 1947 §25,
Company Disciplinary Procedure norms.  Output ONLY the letter text — no commentary.
""",

    "landlord_tenant_notice": """\
You are a senior Indian property-law advocate. Draft a formal landlord-tenant notice
(eviction, rent demand, lease termination, or breach of tenancy).

MANDATORY STRUCTURE:
1. Heading: Appropriate title (e.g. "NOTICE TO VACATE" / "DEMAND NOTICE FOR RENT")
2. Sender (landlord / tenant) block
3. Recipient (tenant / landlord) block
4. Property description: full address, lease period
5. Facts: breach, arrears, or termination grounds
6. Demand / Notice period — state applicable state Rent Control Act notice period
7. Consequences: eviction suit / recovery suit if not complied with

Cite: Transfer of Property Act 1882 §§106-111, Specific Relief Act 1963, applicable State Rent Control Act.
Output ONLY the notice text — no commentary.
""",

    "property_dispute_notice": """\
You are a senior Indian property-law advocate. Draft a legal notice for a property dispute
(encroachment, boundary dispute, adverse possession, title dispute, trespass, etc.).

MANDATORY STRUCTURE:
1. Heading: "LEGAL NOTICE — PROPERTY DISPUTE"
2. Sender block (owner / aggrieved party)
3. Recipient block (encroacher / disputed party)
4. Property description: survey number, area, registration details
5. Facts: nature of dispute, history of ownership, acts of encroachment / trespass
6. Legal basis: ownership documents, registered title, survey records
7. Demand within [N] days:
   a. Vacate / remove encroachment
   b. Pay damages / mesne profits
8. Consequences: Suit for Declaration & Injunction u/ss 6/38/39 Specific Relief Act,
   IPC §447 (criminal trespass), CPC Order 39

Cite: Specific Relief Act 1963, Transfer of Property Act 1882, Registration Act 1908, IPC §441-447.
Output ONLY the notice text — no commentary.
""",

    "non_disclosure_agreement": """\
You are a senior Indian corporate lawyer. Draft a professional Non-Disclosure Agreement (NDA)
governed by Indian law.

MANDATORY STRUCTURE:
1. Title: NON-DISCLOSURE AGREEMENT
2. Parties clause (Disclosing Party and Receiving Party — names, addresses)
3. Effective date
4. Definition of Confidential Information (broad but precise)
5. Exclusions from Confidential Information (public domain, prior knowledge, legal compulsion)
6. Obligations of Receiving Party — use only for permitted purpose, same care as own confidential info
7. Permitted Disclosures (employees / advisors on need-to-know + their own NDA obligations)
8. Term of confidentiality (e.g. 3 years after termination)
9. Return / Destruction of information on request or termination
10. Remedies: injunctive relief + damages; no adequate remedy at law assumed
11. Governing Law: courts at [City], India; Indian Contract Act 1872
12. Entire Agreement, Waiver, Severability, Amendment clauses
13. Schedule A — description of specific project / context

Output ONLY the NDA text — no commentary.
""",

    "rent_agreement": """\
You are a senior Indian property lawyer. Draft a Residential Leave-and-Licence Agreement
(commonly called rent agreement) compliant with Indian law.

MANDATORY STRUCTURE:
1. Title: LEAVE AND LICENCE AGREEMENT
2. Parties (Licensor / Landlord and Licensee / Tenant — names, addresses)
3. Premises description (full address, area, furnishing)
4. Term (start date, duration — typically 11 months to avoid registration)
5. Licence fee (monthly rent) and due date; security deposit amount and refund conditions
6. Terms of use: residential only, no subletting, no structural changes, maintenance obligations
7. Utilities: responsibility for electricity, water, gas
8. Termination: notice period (typically 1 month), grounds for early termination
9. Licensor's right to enter for inspection with prior notice
10. Governing law: Transfer of Property Act 1882, Maharashtra Rent Control Act (or state equivalent)
11. Execution: signed in presence of two witnesses, date and place
12. Witness block; Annexure — inventory of fixtures

Output ONLY the agreement text — no commentary.
""",

    "power_of_attorney": """\
You are a senior Indian lawyer. Draft a Power of Attorney (General or Specific) under the
Powers of Attorney Act 1882 and Indian Registration Act 1908.

MANDATORY STRUCTURE:
1. Title: POWER OF ATTORNEY (GENERAL / SPECIFIC)
2. Principal details (name, address, ID proof reference)
3. Agent / Attorney-in-fact details (name, address, relationship)
4. Scope of authority — list each power granted (property, banking, legal proceedings, etc.)
5. Duration — specific date or "until revoked in writing"
6. Ratification clause — principal ratifies all acts of attorney within the scope
7. Revocation — principal reserves right to revoke at any time; agent's duty on revocation
8. Execution — signed before a Notary / Sub-Registrar as applicable
9. Governing law: Powers of Attorney Act 1882
10. Witness block (two witnesses required); Notarial certificate block

Output ONLY the PoA text — no commentary.
""",

    "affidavit": """\
You are a senior Indian advocate. Draft a formal affidavit for use in court, government, or
administrative proceedings.

MANDATORY STRUCTURE:
1. Heading — identify the court / authority (if applicable): "BEFORE THE HON'BLE …"
   OR simply "AFFIDAVIT" for general purpose
2. Deponent details (full name, age, occupation, address)
3. Verification clause opener: "I, [name], do hereby solemnly affirm and state as follows:"
4. Numbered paragraphs — each paragraph one fact
5. Statement: "I state the above facts to the best of my knowledge, information, and belief
   and nothing material has been concealed."
6. Place, date
7. Deponent signature / thumb impression
8. Verification: "Verified at [place] on this [date] that the contents of
   paragraphs 1 to [N] are true and correct to the best of my knowledge and belief."
9. Before me: Notary / Oath Commissioner / Magistrate block

Cite Indian Oaths Act 1969, CPC Order XIX, or relevant rules as applicable.
Output ONLY the affidavit text — no commentary.
""",

    "general_legal": """\
You are a senior Indian advocate with expertise across all branches of law.
Draft a professional legal document matching the type described in the facts.

Follow these principles:
- Identify the correct document type from the context (petition, application, letter, notice, etc.)
- Use appropriate formal legal language and Indian legal conventions
- Cite all applicable statutes, rules, and case law principles
- Structure with numbered paragraphs and clear headings
- Include a prayer / relief / demand section
- Include date, signature block, and annexure list if needed

Output ONLY the document text — no introductory remarks or commentary.
""",
}

# Consumer notice type uses the specialist pipeline, not this agent.
# Provide a minimal fallback prompt in case it's called here.
_SYSTEM_PROMPTS["consumer_notice"] = _SYSTEM_PROMPTS["general_legal"]


_WORKFLOW_NOTES: dict[str, str] = {
    "agreement": "This is a consensual agreement. Use neutral, balanced, execution-ready contract language and do not write in adversarial notice style.",
    "instrument": "This is a formal legal instrument. Focus on authority, scope, execution formalities, and validity rather than dispute framing.",
    "application": "This is a formal application to an authority. Use respectful official language, numbered requests, and filing-compliance wording.",
    "appeal": "This is a grievance or appeal. Address the authority respectfully, rebut the rejection clearly, and ask for specific corrective action.",
    "complaint": "This is a formal complaint for official action. Keep the narration factual, chronological, and precise.",
    "affidavit": "This is a sworn statement. Use first-person numbered facts, verification language, and oath/affirmation structure.",
    "employment_letter": "This is an employer-side HR document. Use formal workplace language, procedural fairness, and compliance-oriented drafting.",
    "specialist_notice": "This document belongs to the specialist consumer-notice workflow. Preserve legal notice style and structured consumer-law framing.",
}


def _format_field_label(raw_key: str) -> str:
    return raw_key.replace("_", " ").strip().title()


def _append_party_block(
    lines: list[str],
    heading: str,
    name: str | None,
    address: str | None,
    email: str | None,
    phone: str | None,
) -> None:
    lines.append(f"=== {heading.upper()} ===")
    if name:
        lines.append(f"Name: {name}")
    if address:
        lines.append(f"Address: {address}")
    if email:
        lines.append(f"Email: {email}")
    if phone:
        lines.append(f"Phone: {phone}")
    lines.append("")


def _build_user_prompt(req: LegalDocumentRequest) -> str:
    """Compose a drafting prompt that reflects the specific document workflow."""
    config = get_document_type_config(req.document_type)
    workflow = str(config.get("workflow") or "general")
    party_labels = cast(dict[str, str], config.get("party_labels") or {})
    field_specs = cast(list[dict[str, Any]], config.get("field_specs") or [])
    field_label_map = {
        str(spec.get("key") or ""): str(spec.get("label") or spec.get("key") or "")
        for spec in field_specs
    }

    sender_label = req.sender_role or str(party_labels.get("sender") or "Sender / Applicant")
    recipient_label = req.recipient_role or str(party_labels.get("recipient") or "Recipient / Authority")

    lines: list[str] = []
    lines.append(f"DOCUMENT TYPE: {req.document_type.value}")
    lines.append(f"DOCUMENT LABEL: {config.get('label', req.document_type.value)}")
    lines.append(f"WORKFLOW: {workflow}")
    lines.append(f"DATE OF DOCUMENT: {datetime.utcnow().strftime('%d %B %Y')}")

    workflow_note = _WORKFLOW_NOTES.get(workflow)
    if workflow_note:
        lines.append(f"DRAFTING NOTE: {workflow_note}")
    lines.append("")

    _append_party_block(
        lines,
        sender_label,
        req.sender_name,
        req.sender_address,
        req.sender_email,
        req.sender_phone,
    )

    if req.recipient_name or req.recipient_address or req.recipient_email:
        _append_party_block(
            lines,
            recipient_label,
            req.recipient_name,
            req.recipient_address,
            req.recipient_email,
            None,
        )

    lines.append(f"JURISDICTION: {req.jurisdiction}")
    lines.append("")

    if req.purpose:
        lines.append("=== PURPOSE / CONTEXT ===")
        lines.append(req.purpose)
        lines.append("")

    if req.facts:
        lines.append("=== FACTS / BACKGROUND ===")
        lines.append(req.facts)
        lines.append("")

    if req.timeline:
        lines.append("=== TIMELINE ===")
        for entry in req.timeline:
            lines.append(f"- {entry}")
        lines.append("")

    if req.evidence:
        lines.append("=== EVIDENCE / DOCUMENTS ===")
        for item in req.evidence:
            lines.append(f"- {item}")
        lines.append("")

    if req.relief_sought:
        lines.append("=== RELIEF / REQUESTED OUTCOME ===")
        lines.append(req.relief_sought)
        lines.append("")

    if req.extra:
        lines.append("=== STRUCTURED TERMS / KEY FIELDS ===")
        rendered_keys: set[str] = set()
        for spec in field_specs:
            key = str(spec.get("key") or "")
            if not key or key not in req.extra:
                continue
            rendered_keys.add(key)
            lines.append(f"{field_label_map[key]}: {req.extra[key]}")
        for key, value in req.extra.items():
            if key in rendered_keys:
                continue
            lines.append(f"{_format_field_label(key)}: {value}")
        lines.append("")

    if req.language.lower() not in ("english", "en"):
        lines.append(f"OUTPUT LANGUAGE: {req.language} — translate the entire document.")

    return "\n".join(lines)


@dataclass
class DocumentDraft:
    title: str
    body: str
    applicable_law: list[str] = field(default_factory=list)
    filing_notes: str | None = None


class GeneralDocumentAgent:
    """Generates any legal document type using type-specific LLM prompts."""

    _DRAFT_VALIDATION_SYSTEM = (
        "You are a strict legal-document validation hook for Indian legal drafting. "
        "Validate whether the draft matches the requested document type, party structure, "
        "and mandatory legal sections. Return ONLY JSON with keys: "
        "is_valid (boolean), score (0-100 integer), issues (array of concise strings)."
    )

    _MAX_REFINEMENTS = 2

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm
        self.validator_llm = llm.fast_copy()

    # ── Applicable-law extraction ─────────────────────────────────────

    _LAW_EXTRACT_SYSTEM = (
        "You are a legal citation extractor. Given a draft legal document, "
        "return a JSON object with two keys:\n"
        '  "statutes": array of strings — each cited statute / section in short form '
        '(e.g. "NI Act 1881, S.138", "RTI Act 2005, S.6")\n'
        '  "filing_notes": string — one short paragraph on where / how to serve or file '
        "this document (addresses, fees, timelines). If nothing specific, return null.\n"
        "Return ONLY the JSON object."
    )

    async def _extract_metadata(self, body: str) -> tuple[list[str], str | None]:
        try:
            data = await self.llm.complete_json(
                self._LAW_EXTRACT_SYSTEM,
                f"Document:\n{body[:6000]}",   # cap to avoid excessive cost
            )
            statutes: list[str] = data.get("statutes") or []
            filing_notes: str | None = data.get("filing_notes") or None
            return statutes, filing_notes
        except Exception as exc:
            logger.warning("Metadata extraction failed: %s", exc)
            return [], None

    async def _validate_draft(self, req: LegalDocumentRequest, body: str) -> tuple[bool, list[str], int]:
        config = get_document_type_config(req.document_type)
        field_specs = cast(list[dict[str, Any]], config.get("field_specs") or [])
        required_structured_fields = [
            str(spec.get("label") or spec.get("key") or "")
            for spec in field_specs
            if spec.get("required")
        ]

        validation_prompt = "\n".join([
            f"Document type: {req.document_type.value}",
            f"Label: {config.get('label', req.document_type.value)}",
            f"Workflow: {config.get('workflow', 'general')}",
            f"Needs recipient: {bool(config.get('needs_recipient'))}",
            f"Requires facts: {bool(config.get('requires_facts'))}",
            f"Requires relief: {bool(config.get('requires_relief'))}",
            f"Requires purpose: {bool(config.get('requires_purpose'))}",
            f"Required structured fields: {required_structured_fields}",
            "",
            "Draft to validate:",
            body[:10000],
        ])

        try:
            data = await self.validator_llm.complete_json(
                self._DRAFT_VALIDATION_SYSTEM,
                validation_prompt,
                max_tokens=1024,
            )
            issues_raw = data.get("issues") or []
            issues = [str(i).strip() for i in issues_raw if str(i).strip()]
            score_raw = data.get("score", 0)
            try:
                score = int(score_raw)
            except Exception:
                score = 0
            is_valid = bool(data.get("is_valid"))
            return is_valid, issues, score
        except Exception as exc:
            logger.warning("Draft validation hook failed: %s", exc)
            return False, ["Validation hook failed; could not verify document structure."], 0

    async def _refine_draft(self, req: LegalDocumentRequest, current_body: str, issues: list[str]) -> str:
        doc_type = req.document_type.value
        system_prompt = _SYSTEM_PROMPTS.get(doc_type, _SYSTEM_PROMPTS["general_legal"])
        issues_block = "\n".join(f"- {issue}" for issue in issues) if issues else "- Improve legal structure and compliance."
        refinement_prompt = (
            f"{_build_user_prompt(req)}\n\n"
            "=== EXISTING DRAFT (MUST REVISE) ===\n"
            f"{current_body[:12000]}\n\n"
            "=== VALIDATION ISSUES TO FIX ===\n"
            f"{issues_block}\n\n"
            "Return the FULL corrected legal document only. No commentary."
        )
        return await self.llm.complete_text(
            system_prompt=system_prompt,
            user_prompt=refinement_prompt,
            max_tokens=4096,
        )

    # ── Title inference ───────────────────────────────────────────────

    _TITLE_MAP: dict[str, str] = {
        "cheque_bounce_notice": "Legal Notice under Section 138 NI Act",
        "demand_notice": "Demand / Recovery Notice",
        "defamation_notice": "Legal Notice — Defamation",
        "cease_and_desist": "Cease and Desist Notice",
        "trademark_notice": "Legal Notice — IP Infringement",
        "insurance_appeal": "Complaint / Appeal — Insurance Claim",
        "rti_application": "RTI Application under Section 6(1), RTI Act 2005",
        "police_complaint": "Written Complaint to Police / Magistrate",
        "employment_dispute_notice": "Legal Notice — Employment Dispute",
        "employment_termination_letter": "Show-Cause / Termination Letter",
        "landlord_tenant_notice": "Notice — Landlord / Tenant Dispute",
        "property_dispute_notice": "Legal Notice — Property Dispute",
        "non_disclosure_agreement": "Non-Disclosure Agreement",
        "rent_agreement": "Leave and Licence Agreement",
        "power_of_attorney": "Power of Attorney",
        "affidavit": "Affidavit",
        "consumer_notice": "Consumer Legal Notice",
        "general_legal": "Legal Document",
    }

    def _infer_title(self, doc_type: str, recipient: str | None) -> str:
        base = self._TITLE_MAP.get(doc_type, "Legal Document")
        if recipient:
            return f"{base} — {recipient}"
        return base

    # ── Main entry point ──────────────────────────────────────────────

    async def draft(self, req: LegalDocumentRequest) -> DocumentDraft:
        doc_type = req.document_type.value
        system_prompt = _SYSTEM_PROMPTS.get(doc_type, _SYSTEM_PROMPTS["general_legal"])
        user_prompt = _build_user_prompt(req)

        body = await self.llm.complete_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4096,
        )

        body = body.strip()

        for attempt in range(self._MAX_REFINEMENTS + 1):
            is_valid, issues, score = await self._validate_draft(req, body)
            if is_valid:
                break
            if attempt == self._MAX_REFINEMENTS:
                issue_text = "; ".join(issues[:3]) if issues else "Document structure failed validation."
                raise ValueError(f"Generated draft did not pass validation (score={score}): {issue_text}")
            logger.info(
                "Refining draft for %s after validation failure (attempt=%d, score=%d)",
                req.document_type.value,
                attempt + 1,
                score,
            )
            body = (await self._refine_draft(req, body, issues)).strip()

        applicable_law, filing_notes = await self._extract_metadata(body)
        title = self._infer_title(doc_type, req.recipient_name)

        return DocumentDraft(
            title=title,
            body=body,
            applicable_law=applicable_law,
            filing_notes=filing_notes,
        )
