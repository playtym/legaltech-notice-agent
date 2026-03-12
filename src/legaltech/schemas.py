from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class IntakeMode(str, Enum):
    typed = "typed"
    voice = "voice"


class ServiceTier(str, Enum):
    self_send = "self_send"       # ₹199 — user gets PDF to send themselves
    lawyer_assisted = "lawyer"    # ₹599 — reviewed by advocate, sent on their behalf


class Complainant(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    address: str | None = None


class ComplaintInput(BaseModel):
    mode: IntakeMode = IntakeMode.typed
    complainant: Complainant
    company_name_hint: str | None = Field(default=None, max_length=200)
    website: HttpUrl | None = None
    issue_summary: str = Field(min_length=20, max_length=10_000)
    timeline: list[str] = Field(default_factory=list, max_length=50)
    evidence: list[str] = Field(default_factory=list, max_length=50)
    desired_resolution: str = Field(max_length=2000)
    jurisdiction: str = Field(default="India")
    transcript_text: str | None = Field(default=None, max_length=20_000)


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
    # Fetched data surfaced to the user
    company_name_found: str | None = None
    company_domain: str | None = None
    contacts_found: list[str] = Field(default_factory=list)
    respondent_cin: str | None = None
    respondent_registered_name: str | None = None
    respondent_registered_office: str | None = None
    grievance_officer_email: str | None = None
    policies_found: list[str] = Field(default_factory=list)
