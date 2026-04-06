from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
import re

class IntakeMode(str, Enum):
    typed = "typed"
    voice = "voice"


class DocumentType(str, Enum):
    """All legal document types this platform can generate."""
    # Existing consumer notice — routed to the specialist pipeline
    consumer_notice = "consumer_notice"
    # Cheques / money recovery
    cheque_bounce_notice = "cheque_bounce_notice"   # S.138 NI Act 15-day demand
    demand_notice = "demand_notice"                 # Generic money/debt demand
    # Defamation / IP / speech
    defamation_notice = "defamation_notice"
    cease_and_desist = "cease_and_desist"
    trademark_notice = "trademark_notice"
    # Insurance
    insurance_appeal = "insurance_appeal"           # IRDAI complaint / appeal letter
    # Government / RTI / police
    rti_application = "rti_application"             # Right to Information Act 2005
    police_complaint = "police_complaint"           # Complaint to police / magistrate
    # Employment
    employment_dispute_notice = "employment_dispute_notice"
    employment_termination_letter = "employment_termination_letter"
    # Property / housing
    landlord_tenant_notice = "landlord_tenant_notice"
    property_dispute_notice = "property_dispute_notice"
    # Agreements / instruments
    non_disclosure_agreement = "non_disclosure_agreement"
    rent_agreement = "rent_agreement"
    power_of_attorney = "power_of_attorney"
    # Formal instruments
    affidavit = "affidavit"
    # Catch-all
    general_legal = "general_legal"


_DOCUMENT_TYPE_META: dict[str, dict] = {
    "consumer_notice": {
        "label": "Consumer Legal Notice",
        "description": "Demand notice against a company for defective goods, service failure, refund issues etc. under Consumer Protection Act 2019.",
        "needs_recipient": True,
    },
    "cheque_bounce_notice": {
        "label": "Cheque Bounce Notice (S.138 NI Act)",
        "description": "Statutory 15-day demand notice after dishonour of cheque under Section 138 of the Negotiable Instruments Act 1881.",
        "needs_recipient": True,
    },
    "demand_notice": {
        "label": "Demand / Recovery Notice",
        "description": "Formal demand for repayment of money, loan, or dues owed by an individual or entity.",
        "needs_recipient": True,
    },
    "defamation_notice": {
        "label": "Defamation Notice",
        "description": "Legal notice demanding retraction, apology, and damages for defamatory statements (libel or slander).",
        "needs_recipient": True,
    },
    "cease_and_desist": {
        "label": "Cease & Desist Notice",
        "description": "Formal demand to stop an unlawful activity — harassment, unauthorized use, trespass, nuisance, etc.",
        "needs_recipient": True,
    },
    "trademark_notice": {
        "label": "Trademark / IP Infringement Notice",
        "description": "Notice of intellectual property infringement (trademark, copyright, design) with demand to cease and pay damages.",
        "needs_recipient": True,
    },
    "insurance_appeal": {
        "label": "Insurance Claim Rejection Appeal",
        "description": "Formal appeal/complaint to IRDAI or Insurance Ombudsman against wrongful rejection or delay of an insurance claim.",
        "needs_recipient": True,
    },
    "rti_application": {
        "label": "RTI Application",
        "description": "Application under the Right to Information Act 2005 to a Public Information Officer of a government body.",
        "needs_recipient": True,
    },
    "police_complaint": {
        "label": "Police Complaint / FIR Draft",
        "description": "Written complaint to a police station or magistrate court narrating a cognizable offence.",
        "needs_recipient": True,
    },
    "employment_dispute_notice": {
        "label": "Employment Dispute Notice",
        "description": "Legal notice for wrongful termination, unpaid wages, PF/gratuity dues, or workplace rights violations.",
        "needs_recipient": True,
    },
    "employment_termination_letter": {
        "label": "Employment Termination / Show-Cause Letter",
        "description": "Formal termination letter or show-cause notice from employer to employee.",
        "needs_recipient": True,
    },
    "landlord_tenant_notice": {
        "label": "Landlord / Tenant Notice",
        "description": "Notice for eviction, unpaid rent, lease termination, or breach of tenancy agreement.",
        "needs_recipient": True,
    },
    "property_dispute_notice": {
        "label": "Property Dispute Notice",
        "description": "Legal notice for encroachment, boundary disputes, adverse possession, or title disputes.",
        "needs_recipient": True,
    },
    "non_disclosure_agreement": {
        "label": "Non-Disclosure Agreement (NDA)",
        "description": "Bilateral or unilateral confidentiality agreement protecting proprietary information.",
        "needs_recipient": True,
    },
    "rent_agreement": {
        "label": "Rent / Leave-and-Licence Agreement",
        "description": "Residential or commercial rental agreement between landlord and tenant.",
        "needs_recipient": True,
    },
    "power_of_attorney": {
        "label": "Power of Attorney",
        "description": "General or specific power of attorney authorising an agent to act on the principal's behalf.",
        "needs_recipient": True,
    },
    "affidavit": {
        "label": "Affidavit",
        "description": "Sworn statement of facts for use in court, government, or administrative proceedings.",
        "needs_recipient": False,
    },
    "general_legal": {
        "label": "General Legal Document",
        "description": "Any other legal document — petition, application, letter, or instrument — not covered by a specific type.",
        "needs_recipient": False,
    },
}


DocumentExtraValue = str | int | float | bool


def _field_spec(
    key: str,
    label: str,
    required: bool,
    input_type: str = "text",
    help_text: str = "",
) -> dict[str, str | bool]:
    return {
        "key": key,
        "label": label,
        "required": required,
        "input_type": input_type,
        "help_text": help_text,
    }


_DOCUMENT_TYPE_WORKFLOW: dict[str, str] = {
    "consumer_notice": "specialist_notice",
    "cheque_bounce_notice": "notice",
    "demand_notice": "notice",
    "defamation_notice": "notice",
    "cease_and_desist": "notice",
    "trademark_notice": "notice",
    "insurance_appeal": "appeal",
    "rti_application": "application",
    "police_complaint": "complaint",
    "employment_dispute_notice": "notice",
    "employment_termination_letter": "employment_letter",
    "landlord_tenant_notice": "notice",
    "property_dispute_notice": "notice",
    "non_disclosure_agreement": "agreement",
    "rent_agreement": "agreement",
    "power_of_attorney": "instrument",
    "affidavit": "affidavit",
    "general_legal": "general",
}


_DOCUMENT_TYPE_REQUIREMENTS: dict[str, dict[str, bool]] = {
    "consumer_notice": {"requires_facts": True, "requires_relief": True, "requires_purpose": False},
    "cheque_bounce_notice": {"requires_facts": True, "requires_relief": True, "requires_purpose": False},
    "demand_notice": {"requires_facts": True, "requires_relief": True, "requires_purpose": False},
    "defamation_notice": {"requires_facts": True, "requires_relief": True, "requires_purpose": False},
    "cease_and_desist": {"requires_facts": True, "requires_relief": True, "requires_purpose": False},
    "trademark_notice": {"requires_facts": True, "requires_relief": True, "requires_purpose": False},
    "insurance_appeal": {"requires_facts": True, "requires_relief": True, "requires_purpose": False},
    "rti_application": {"requires_facts": False, "requires_relief": False, "requires_purpose": False},
    "police_complaint": {"requires_facts": True, "requires_relief": True, "requires_purpose": False},
    "employment_dispute_notice": {"requires_facts": True, "requires_relief": True, "requires_purpose": False},
    "employment_termination_letter": {"requires_facts": True, "requires_relief": False, "requires_purpose": False},
    "landlord_tenant_notice": {"requires_facts": True, "requires_relief": True, "requires_purpose": False},
    "property_dispute_notice": {"requires_facts": True, "requires_relief": True, "requires_purpose": False},
    "non_disclosure_agreement": {"requires_facts": False, "requires_relief": False, "requires_purpose": True},
    "rent_agreement": {"requires_facts": False, "requires_relief": False, "requires_purpose": True},
    "power_of_attorney": {"requires_facts": False, "requires_relief": False, "requires_purpose": True},
    "affidavit": {"requires_facts": True, "requires_relief": False, "requires_purpose": True},
    "general_legal": {"requires_facts": False, "requires_relief": False, "requires_purpose": True},
}


_DOCUMENT_TYPE_PARTY_LABELS: dict[str, dict[str, str]] = {
    "consumer_notice": {"sender": "Complainant", "recipient": "Company / Opposite Party"},
    "cheque_bounce_notice": {"sender": "Payee / Holder", "recipient": "Drawer of Cheque"},
    "demand_notice": {"sender": "Claimant / Creditor", "recipient": "Debtor / Opposite Party"},
    "defamation_notice": {"sender": "Aggrieved Person", "recipient": "Defaming Party"},
    "cease_and_desist": {"sender": "Rights Holder / Aggrieved Party", "recipient": "Opposite Party"},
    "trademark_notice": {"sender": "Rights Holder", "recipient": "Infringing Party"},
    "insurance_appeal": {"sender": "Policyholder / Claimant", "recipient": "Insurer / Grievance Officer"},
    "rti_application": {"sender": "Applicant", "recipient": "PIO / Public Authority"},
    "police_complaint": {"sender": "Complainant", "recipient": "SHO / Magistrate"},
    "employment_dispute_notice": {"sender": "Employee / Claimant", "recipient": "Employer / Company"},
    "employment_termination_letter": {"sender": "Employer", "recipient": "Employee"},
    "landlord_tenant_notice": {"sender": "Landlord / Tenant", "recipient": "Tenant / Landlord"},
    "property_dispute_notice": {"sender": "Owner / Claimant", "recipient": "Opposite Party"},
    "non_disclosure_agreement": {"sender": "Disclosing Party", "recipient": "Receiving Party"},
    "rent_agreement": {"sender": "Landlord / Licensor", "recipient": "Tenant / Licensee"},
    "power_of_attorney": {"sender": "Principal", "recipient": "Attorney / Agent"},
    "affidavit": {"sender": "Deponent", "recipient": "Court / Authority"},
    "general_legal": {"sender": "Sender / Applicant", "recipient": "Recipient / Authority"},
}


_DOCUMENT_TYPE_FIELD_SPECS: dict[str, list[dict[str, str | bool]]] = {
    "cheque_bounce_notice": [
        _field_spec("cheque_number", "Cheque Number", True, "text", "Cheque number printed on the dishonoured cheque."),
        _field_spec("cheque_date", "Cheque Date", True, "date", "Date written on the cheque."),
        _field_spec("cheque_amount", "Cheque Amount (INR)", True, "currency", "Cheque amount in rupees."),
        _field_spec("bank_name", "Bank Name", True, "text", "Drawer bank or branch name."),
        _field_spec("dishonour_date", "Dishonour Date", True, "date", "Date when the cheque return memo was issued."),
        _field_spec("dishonour_reason", "Dishonour Reason", True, "text", "Reason on the bank return memo, e.g. insufficient funds."),
    ],
    "insurance_appeal": [
        _field_spec("policy_number", "Policy Number", True, "text", "Insurance policy number."),
        _field_spec("claim_number", "Claim Number", True, "text", "Claim reference number from insurer."),
        _field_spec("claim_amount", "Claim Amount (INR)", True, "currency", "Amount claimed from insurer."),
        _field_spec("incident_date", "Incident / Loss Date", True, "date", "Date of hospitalization, accident, or insured event."),
        _field_spec("rejection_date", "Rejection Date", True, "date", "Date of rejection letter or email."),
        _field_spec("rejection_reason", "Rejection Reason", True, "textarea", "Grounds cited by insurer for rejecting or delaying the claim."),
    ],
    "rti_application": [
        _field_spec("public_authority", "Public Authority", True, "text", "Department, ministry, PSU, municipality, police office, etc."),
        _field_spec("pio_name", "PIO Name", False, "text", "Public Information Officer name if known."),
        _field_spec("information_requested", "Information Requested", True, "textarea", "List the exact information/documents sought."),
        _field_spec("period_requested", "Relevant Time Period", False, "text", "Example: 1 Jan 2024 to 31 Dec 2025."),
        _field_spec("delivery_format", "Information Format", False, "text", "Certified copies, inspection, PDF by email, etc."),
    ],
    "employment_dispute_notice": [
        _field_spec("employee_id", "Employee ID", False, "text", "Internal employee code if available."),
        _field_spec("date_of_joining", "Date of Joining", False, "date", "Original employment start date."),
        _field_spec("last_working_day", "Last Working Day", False, "date", "Actual or disputed last working day."),
        _field_spec("monthly_salary", "Monthly Salary (INR)", False, "currency", "Gross or net monthly salary."),
        _field_spec("dues_breakup", "Dues Breakdown", False, "textarea", "Unpaid salary, gratuity, leave encashment, notice pay, bonus, etc."),
    ],
    "employment_termination_letter": [
        _field_spec("employee_id", "Employee ID", True, "text", "Internal employee code."),
        _field_spec("designation", "Designation", True, "text", "Employee's job title."),
        _field_spec("date_of_joining", "Date of Joining", False, "date", "Employment commencement date."),
        _field_spec("termination_effective_date", "Termination Effective Date", True, "date", "Date on which termination or show-cause takes effect."),
        _field_spec("termination_reason", "Reason / Grounds", True, "textarea", "Misconduct, poor performance, redundancy, or disciplinary cause."),
        _field_spec("notice_period", "Notice Period / Response Time", False, "text", "Example: 30 days or 3 working days."),
    ],
    "landlord_tenant_notice": [
        _field_spec("property_address", "Property Address", True, "textarea", "Complete tenanted property address."),
        _field_spec("tenancy_start_date", "Tenancy Start Date", False, "date", "Date on which the tenancy/licence started."),
        _field_spec("monthly_rent", "Monthly Rent (INR)", False, "currency", "Monthly rent or licence fee."),
        _field_spec("arrears_amount", "Arrears Amount (INR)", False, "currency", "Outstanding rent amount, if any."),
        _field_spec("notice_ground", "Ground of Notice", True, "textarea", "Eviction, rent arrears, breach of use, termination, lock-in breach, etc."),
        _field_spec("notice_period", "Notice Period", False, "text", "Example: 15 days, 30 days, one month."),
    ],
    "property_dispute_notice": [
        _field_spec("property_address", "Property Address", True, "textarea", "Disputed property address."),
        _field_spec("survey_number", "Survey / Plot Number", False, "text", "Survey, plot, khasra, or khata number if known."),
        _field_spec("title_document", "Title / Ownership Document", False, "text", "Sale deed, gift deed, partition deed, allotment letter, etc."),
        _field_spec("encroachment_description", "Nature of Dispute", True, "textarea", "Encroachment, blocked access, trespass, boundary shift, etc."),
    ],
    "non_disclosure_agreement": [
        _field_spec("agreement_type", "Agreement Type", True, "text", "Unilateral or bilateral NDA."),
        _field_spec("effective_date", "Effective Date", True, "date", "NDA commencement date."),
        _field_spec("permitted_purpose", "Permitted Purpose", True, "textarea", "Project, diligence, investor discussion, vendor evaluation, etc."),
        _field_spec("confidentiality_term", "Confidentiality Term", True, "text", "Example: 3 years after disclosure / 5 years after termination."),
        _field_spec("governing_law_city", "Governing Law / Jurisdiction City", True, "text", "City whose courts will have jurisdiction."),
    ],
    "rent_agreement": [
        _field_spec("property_address", "Property Address", True, "textarea", "Complete address of flat/house/office being rented."),
        _field_spec("agreement_start_date", "Agreement Start Date", True, "date", "Commencement date of tenancy/licence."),
        _field_spec("agreement_end_date", "Agreement End Date", True, "date", "End date or planned expiry date."),
        _field_spec("monthly_rent", "Monthly Rent / Licence Fee (INR)", True, "currency", "Monthly amount payable by tenant/licensee."),
        _field_spec("security_deposit", "Security Deposit (INR)", True, "currency", "Refundable security deposit amount."),
        _field_spec("notice_period", "Notice Period", True, "text", "Typical termination notice period, e.g. 30 days."),
        _field_spec("use_type", "Use Type", False, "text", "Residential, commercial, office, warehouse, etc."),
        _field_spec("maintenance_responsibility", "Maintenance Responsibility", False, "text", "Who pays society charges, repairs, utilities, etc."),
    ],
    "power_of_attorney": [
        _field_spec("attorney_relationship", "Attorney Relationship", False, "text", "Daughter, spouse, manager, lawyer, business partner, etc."),
        _field_spec("powers_granted", "Powers Granted", True, "textarea", "Detailed list of powers: banking, property sale, litigation, registration, etc."),
        _field_spec("valid_until", "Validity / Expiry", False, "text", "Specific end date or 'until revoked'."),
        _field_spec("execution_place", "Execution Place", True, "text", "City and state where PoA is executed."),
        _field_spec("witness_details", "Witness Details", False, "textarea", "Names/addresses of witnesses if already known."),
    ],
    "affidavit": [
        _field_spec("authority_name", "Court / Authority", False, "text", "Court, passport office, registrar, employer, bank, etc."),
        _field_spec("affidavit_purpose", "Affidavit Purpose", True, "textarea", "Name correction, address proof, lost document declaration, marriage declaration, etc."),
        _field_spec("deponent_age", "Deponent Age", False, "text", "Age of the deponent."),
        _field_spec("deponent_occupation", "Deponent Occupation", False, "text", "Occupation of the deponent."),
        _field_spec("verification_place", "Verification Place", True, "text", "Place where affidavit is verified/sworn."),
    ],
}


_DOCUMENT_TYPE_EXAMPLES: dict[str, list[str]] = {
    "cheque_bounce_notice": [
        "Notice after a bounced cheque for repayment of a friendly loan.",
        "Statutory 15-day demand after cheque dishonour for invoice dues.",
    ],
    "rti_application": [
        "RTI seeking action taken report from a municipal authority.",
        "RTI requesting certified copies of tender evaluation documents.",
    ],
    "non_disclosure_agreement": [
        "Bilateral NDA for startup fundraising discussions.",
        "Unilateral NDA before sharing product roadmap with a vendor.",
    ],
    "rent_agreement": [
        "11-month residential leave-and-licence agreement for an apartment.",
        "Commercial office rent agreement with deposit and maintenance clauses.",
    ],
    "power_of_attorney": [
        "Specific PoA authorising a family member to sell a property.",
        "General PoA to operate bank accounts during overseas travel.",
    ],
    "affidavit": [
        "Affidavit for name correction in passport or educational records.",
        "Affidavit declaring loss of original property papers.",
    ],
    "employment_termination_letter": [
        "Termination letter for redundancy with notice pay and settlement details.",
        "Show-cause notice for repeated misconduct and absenteeism.",
    ],
}


def get_document_type_config(document_type: DocumentType | str) -> dict[str, object]:
    doc_key = document_type.value if isinstance(document_type, DocumentType) else str(document_type)
    meta = dict(_DOCUMENT_TYPE_META.get(doc_key, {}))
    meta["workflow"] = _DOCUMENT_TYPE_WORKFLOW.get(doc_key, "general")
    meta["party_labels"] = _DOCUMENT_TYPE_PARTY_LABELS.get(
        doc_key,
        {"sender": "Sender / Applicant", "recipient": "Recipient / Authority"},
    )
    meta.update(_DOCUMENT_TYPE_REQUIREMENTS.get(doc_key, {}))
    meta["field_specs"] = list(_DOCUMENT_TYPE_FIELD_SPECS.get(doc_key, []))
    meta["examples"] = list(_DOCUMENT_TYPE_EXAMPLES.get(doc_key, []))
    return meta


class LegalDocumentRequest(BaseModel):
    """Generic request body that covers every document type this platform supports."""
    document_type: DocumentType
    # ── Who is sending / applying ────────────────────────────────────
    sender_name: str = Field(..., min_length=2, max_length=200)
    sender_email: str = Field(..., max_length=255, pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    sender_phone: str | None = Field(default=None, max_length=25)
    sender_address: str | None = Field(default=None, max_length=1000)
    sender_role: str | None = Field(default=None, max_length=100)
    # ── Opposite party / recipient (optional for e.g. affidavit) ────
    recipient_name: str | None = Field(default=None, max_length=300)
    recipient_address: str | None = Field(default=None, max_length=1000)
    recipient_email: str | None = Field(default=None, max_length=255)
    recipient_role: str | None = Field(default=None, max_length=100)
    # ── Situation / purpose ──────────────────────────────────────────
    facts: str | None = Field(default=None, max_length=20000,
                              description="Full factual background — what happened, who did what, when.")
    relief_sought: str | None = Field(default=None, max_length=5000,
                                      description="What outcome or remedy is requested.")
    purpose: str | None = Field(default=None, max_length=5000,
                                description="For agreements/applications/instruments: why the document is being created.")
    jurisdiction: str = Field(default="India", max_length=200)
    # ── Supporting details ───────────────────────────────────────────
    timeline: list[str] = Field(default_factory=list, max_items=50)
    evidence: list[str] = Field(default_factory=list, max_items=50)
    # ── Document-type-specific named fields ──────────────────────────
    # For cheque bounce: cheque_number, cheque_date, cheque_amount, bank_name, dishonour_date
    # For RTI: public_authority, information_sought, application_fee_paid
    # For NDA: effective_date, duration_years, governing_law
    # … send as free-form key→value pairs; the agent will use what is relevant.
    extra: dict[str, DocumentExtraValue] = Field(
        default_factory=dict,
        description="Document-type-specific structured fields (dates, amounts, property details, powers, etc.).",
    )
    language: str = Field(default="English", max_length=50)

    @field_validator("sender_name", "sender_email", mode="before")
    def clean_required_identity(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned

    @field_validator(
        "sender_phone",
        "sender_address",
        "sender_role",
        "recipient_name",
        "recipient_address",
        "recipient_email",
        "recipient_role",
        "facts",
        "relief_sought",
        "purpose",
        "jurisdiction",
        "language",
        mode="before",
    )
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("facts")
    def validate_facts(cls, value: str | None) -> str | None:
        if value and len(value) < 20:
            raise ValueError("Facts/background is too brief. Please provide more detail.")
        return value

    @field_validator("relief_sought")
    def validate_relief(cls, value: str | None) -> str | None:
        if value and len(value) < 5:
            raise ValueError("Requested outcome is too brief.")
        return value

    @field_validator("purpose")
    def validate_purpose(cls, value: str | None) -> str | None:
        if value and len(value) < 5:
            raise ValueError("Purpose/context is too brief.")
        return value

    @field_validator("extra", mode="before")
    def clean_extra(cls, value: dict | None) -> dict[str, DocumentExtraValue]:
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise ValueError("extra must be an object.")
        cleaned: dict[str, DocumentExtraValue] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key).strip()
            if not key or raw_value is None:
                continue
            if isinstance(raw_value, str):
                normalized = raw_value.strip()
                if not normalized:
                    continue
                cleaned[key] = normalized
                continue
            cleaned[key] = raw_value
        return cleaned

    @model_validator(mode="after")
    def validate_document_requirements(self) -> "LegalDocumentRequest":
        config = get_document_type_config(self.document_type)
        label = str(config.get("label") or self.document_type.value.replace("_", " ").title())

        if config.get("needs_recipient") and not self.recipient_name:
            raise ValueError(f"{label} requires the recipient/opposite party name.")

        if config.get("requires_facts") and not self.facts:
            raise ValueError(f"{label} requires factual background.")

        if config.get("requires_relief") and not self.relief_sought:
            raise ValueError(f"{label} requires the requested relief or outcome.")

        if config.get("requires_purpose") and not self.purpose:
            raise ValueError(f"{label} requires a clear purpose/context.")

        field_specs = config.get("field_specs") or []
        missing_fields: list[str] = []
        for spec in field_specs:
            if not spec.get("required"):
                continue
            key = str(spec.get("key") or "")
            if key not in self.extra:
                missing_fields.append(str(spec.get("label") or key))
                continue
            value = self.extra[key]
            if isinstance(value, str) and not value.strip():
                missing_fields.append(str(spec.get("label") or key))

        if missing_fields:
            joined = ", ".join(missing_fields)
            raise ValueError(f"{label} requires these structured fields: {joined}.")

        if not self.facts and not self.purpose and not self.extra:
            raise ValueError(f"{label} requires either facts, purpose, or structured document details.")

        return self


class GeneratedDocument(BaseModel):
    """Output produced by the general document pipeline."""
    document_type: DocumentType
    title: str
    body: str                                   # Full formatted document text
    applicable_law: list[str] = Field(default_factory=list)   # Cited statutes / sections
    filing_notes: str | None = None             # Where/how to file or serve this document
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceTier(str, Enum):
    self_send = "self_send"       # ₹199 — user gets PDF to send themselves
    lawyer_assisted = "lawyer"    # ₹599 — reviewed by advocate, sent on their behalf
    print_post = "print_post"     # ₹999 — auto-printed, sent via registered post with tracking


class Complainant(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., max_length=255, pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9\-\s()]{7,25}$")
    address: str | None = Field(default=None, max_length=1000)

    @field_validator("full_name")
    def clean_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Full name cannot be empty whitespace.")
        
        # Anti-spam checks
        lower_name = cleaned.lower()
        blocked_names = {'test', 'john doe', 'jane doe', 'asdf', 'demo', 'abc', 'abcd', '123', 'fake', 'anonymous', 'something'}
        if lower_name in blocked_names or "test" in lower_name:
            raise ValueError("Test or fake names are not permitted for legal notice generation.")
        if len(cleaned) < 4:
            raise ValueError("Please provide a complete full name.")
            
        return cleaned

class ComplaintInput(BaseModel):
    mode: IntakeMode = IntakeMode.typed
    complainant: Complainant
    company_name_hint: str | None = Field(default=None, max_length=200)
    website: HttpUrl | None = None
    issue_summary: str = Field(min_length=20, max_length=10_000)
    timeline: list[str] = Field(default_factory=list, max_items=50)
    evidence: list[str] = Field(default_factory=list, max_items=50)
    desired_resolution: str = Field(min_length=5, max_length=2000)
    company_objection: str | None = Field(default=None, max_length=5000)
    jurisdiction: str = Field(default="India", max_length=150)
    transcript_text: str | None = Field(default=None, max_length=20_000)

    @field_validator("issue_summary")
    def clean_issue(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 10:
            raise ValueError("Issue summary is too brief, please provide more detail.")
        return cleaned

class CompanyProfile(BaseModel):
    legal_name: str | None = None
    brand_name: str | None = None
    domain: str | None = None
    headquarters: str | None = None


class ContactInfo(BaseModel):
    label: str
    email: str | None = None
    phone: str | None = None
    page_url: str | None = None
    confidence: float = 0.0


class PolicyEvidence(BaseModel):
    title: str
    excerpt: str
    source_url: str


class BareActReference(BaseModel):
    act: str
    section: str
    title: str
    bare_text: str
    amendment_note: str | None = None
    state_rules: list[str] = Field(default_factory=list)


class ClaimElementResult(BaseModel):
    section_label: str
    score: float
    overall_pass: bool
    element_details: list[dict[str, str]] = Field(default_factory=list)


class RespondentIdentityInfo(BaseModel):
    cin: str | None = None
    llpin: str | None = None
    registered_name: str | None = None
    registered_office: str | None = None
    grievance_officer_name: str | None = None
    grievance_officer_email: str | None = None
    grievance_officer_phone: str | None = None
    source_urls: list[str] = Field(default_factory=list)
    verification_flags: list[str] = Field(default_factory=list)


class EvidenceScoreInfo(BaseModel):
    overall_score: float = 0.0
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    contradictions: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class LimitationInfo(BaseModel):
    category: str
    period_years: int
    start_event: str
    deadline: str | None = None
    days_remaining: int | None = None
    urgent: bool = False
    warning: str | None = None


class ArbitrationInfo(BaseModel):
    has_arbitration_clause: bool = False
    clause_text: str | None = None
    has_jurisdiction_clause: bool = False
    jurisdiction_text: str | None = None
    legal_impact: str | None = None
    consumer_override_note: str | None = None


class JurisdictionInfo(BaseModel):
    forum: str
    pecuniary_basis: str
    territorial_basis: str
    filing_note: str | None = None


class CurePeriodInfo(BaseModel):
    days: int
    category: str
    rationale: str


class DeliveryInfo(BaseModel):
    tier: ServiceTier = ServiceTier.self_send
    price_inr: int = 199
    pdf_generated: bool = False
    email_sent: bool = False
    email_recipients: list[str] = Field(default_factory=list)
    email_message_id: str | None = None
    delivery_status: str = "pending"
    tracking_id: str | None = None
    dispatch_partner: str | None = None


class TCCounterInfo(BaseModel):
    defense_clause: str
    clause_excerpt: str
    legal_counter: str
    statutory_basis: str
    precedent_note: str


class NoticePacket(BaseModel):
    complaint: ComplaintInput
    company: CompanyProfile
    contacts: list[ContactInfo]
    policy_evidence: list[PolicyEvidence]
    bare_act_references: list[BareActReference] = Field(default_factory=list)
    claim_element_results: list[ClaimElementResult] = Field(default_factory=list)
    respondent_identity: RespondentIdentityInfo | None = None
    evidence_score: EvidenceScoreInfo | None = None
    limitation_info: LimitationInfo | None = None
    arbitration_info: ArbitrationInfo | None = None
    jurisdiction_info: JurisdictionInfo | None = None
    cure_period_info: CurePeriodInfo | None = None
    tc_counters: list[TCCounterInfo] = Field(default_factory=list)
    required_user_uploads: list[str] = Field(default_factory=list)
    legal_notice: str
    delivery: DeliveryInfo = Field(default_factory=DeliveryInfo)
    generated_at: datetime


# ── Progressive questioning schemas ──────────────────────────────────


class FollowUpQuestionOut(BaseModel):
    id: str
    category: str
    priority: str  # "critical" or "important"
    question: str
    why_it_matters: str


class CaseAnalysisResponse(BaseModel):
    """Returned by /notice/analyze — tells the client whether
    the case is ready for generation or needs more info."""
    case_strength: str  # "weak", "moderate", "strong"
    case_strength_reasoning: str
    ready_to_generate: bool
    questions: list[FollowUpQuestionOut] = Field(default_factory=list)
    llm_cost_estimate: dict | None = None
    # Case classification — blocks criminal & individual-vs-individual cases
    case_type: str = "consumer"  # "consumer", "criminal", "individual_dispute"
    case_type_reason: str = ""
    blocked: bool = False
    # Fetched data surfaced to the user
    company_name_found: str | None = None
    company_domain: str | None = None
    contacts_found: list[str] = Field(default_factory=list)
    respondent_cin: str | None = None
    respondent_registered_name: str | None = None
    respondent_registered_office: str | None = None
    grievance_officer_email: str | None = None
    policies_found: list[str] = Field(default_factory=list)
