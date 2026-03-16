from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

import hashlib
import hmac
import logging
import os
import secrets
import time

logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

from legaltech.pipeline import LegalNoticePipeline
from legaltech.schemas import Complainant, ComplaintInput, IntakeMode, ServiceTier
from legaltech.services.pdf_generator import generate_pdf
from legaltech.services import store as notice_store
from legaltech.services.upload_store import upload_store
from legaltech.services import database as db
from legaltech.config.settings import get_settings

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup: initialize the database
    await db.get_db()
    yield
    # Shutdown: close the database connection
    await db.close_db()


app = FastAPI(title="Indian Legal Notice Agent", version="0.4.0", lifespan=lifespan)
pipeline = LegalNoticePipeline()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lawly.store",
        "https://www.lawly.store",
        "https://d3ipaitzvby9v2.cloudfront.net",
        "https://d1exs4vnzimint.cloudfront.net",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ── Admin authentication ─────────────────────────────────────────────
# Simple token-based auth: login with password → get token → pass as Bearer header

_admin_tokens: dict[str, float] = {}  # token → expiry timestamp
_TOKEN_TTL = 24 * 60 * 60  # 24 hours


class AdminLoginRequest(BaseModel):
    password: str


@app.post("/api/admin/login")
async def admin_login(body: AdminLoginRequest):
    settings = get_settings()
    stored_pw = notice_store.get_stored_password()
    expected = stored_pw if stored_pw else settings.admin_password
    if not hmac.compare_digest(body.password, expected):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = secrets.token_urlsafe(32)
    _admin_tokens[token] = time.time() + _TOKEN_TTL
    # Cleanup expired tokens
    now = time.time()
    expired = [t for t, exp in _admin_tokens.items() if exp < now]
    for t in expired:
        _admin_tokens.pop(t, None)
    notice_store.log_activity("Admin login", "", "auth")
    return {"token": token, "expires_in": _TOKEN_TTL}


async def require_admin(authorization: str | None = Header(None)):
    """Dependency that validates the admin Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization[7:]
    expiry = _admin_tokens.get(token)
    if not expiry or expiry < time.time():
        _admin_tokens.pop(token, None)
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    return True


_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB per file
_MAX_UPLOAD_FILES = 10
_ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
}


class NoticeRequest(BaseModel):
    complainant: Complainant
    issue_summary: str
    desired_resolution: str
    company_name_hint: str | None = None
    website: HttpUrl | None = None
    timeline: list[str] = []
    evidence: list[str] = []
    jurisdiction: str = "India"
    tier: ServiceTier = ServiceTier.self_send
    follow_up_answers: dict[str, str] | None = None
    upload_ids: list[str] = []  # IDs from /documents/upload
    # Customer controls
    notice_tone: str | None = None        # "firm" | "aggressive" | "diplomatic"
    cure_period_days: int | None = None    # override auto-detected cure period
    compensation_amount: int | None = None # specific ₹ amount for compensation demand
    interest_rate_percent: float | None = None  # annual interest rate on refund
    language: str = "English"              # output language


class AnalyzeRequest(BaseModel):
    """Request body for /notice/analyze — same complaint fields, plus optional previous answers."""
    complainant: Complainant | dict | None = None
    issue_summary: str
    desired_resolution: str
    company_name_hint: str | None = None
    website: HttpUrl | None = None
    timeline: list[str] = []
    evidence: list[str] = []
    jurisdiction: str = "India"
    previous_answers: dict[str, str] | None = None  # answers from a prior /analyze round
    upload_ids: list[str] = []  # IDs from /documents/upload


class VoiceNoticeRequest(NoticeRequest):
    transcript_text: str


class TranslateRequest(BaseModel):
    text: str


class TranscriptIntakeRequest(BaseModel):
    transcript_text: str
    complainant: Complainant
    company_name_hint: str | None = None
    website: HttpUrl | None = None
    desired_resolution: str | None = None
    timeline: list[str] = []
    evidence: list[str] = []
    jurisdiction: str = "India"


class SpeechRefineRequest(BaseModel):
    transcript_text: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": pipeline.llm.model_name}


class CompanyLookupRequest(BaseModel):
    brand_name: str
    website: HttpUrl | None = None


@app.post("/company/lookup")
async def company_lookup(req: CompanyLookupRequest):
    """Look up legal entity details (CIN, registered name, office) from brand name + website."""
    import logging
    logger = logging.getLogger(__name__)
    result: dict[str, str | None] = {
        "registered_name": None,
        "cin": None,
        "registered_office": None,
        "grievance_officer_name": None,
        "grievance_officer_email": None,
    }
    if not req.website:
        return result
    try:
        identity = await pipeline.respondent_id.run(
            website=str(req.website),
            company_name_hint=req.brand_name,
            web=pipeline.web,
        )
        result["registered_name"] = identity.registered_name
        result["cin"] = identity.cin
        result["registered_office"] = identity.registered_office
        result["grievance_officer_name"] = identity.grievance_officer_name
        result["grievance_officer_email"] = identity.grievance_officer_email
    except Exception as e:
        logger.warning("Company lookup failed: %s", e)
    return result


@app.post("/documents/upload")
async def upload_documents(files: list[UploadFile]):
    """Upload evidence documents (images, PDFs). Returns file metadata with IDs."""
    if len(files) > _MAX_UPLOAD_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {_MAX_UPLOAD_FILES} files allowed")

    results = []
    for f in files:
        ct = f.content_type or "application/octet-stream"
        if ct not in _ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ct}' not allowed. Accepted: JPEG, PNG, GIF, WebP, PDF",
            )
        data = await f.read()
        if len(data) > _MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail=f"File '{f.filename}' exceeds 10 MB limit")
        stored = upload_store.store(filename=f.filename or "untitled", content_type=ct, data=data)

        # Persist document metadata to DB
        try:
            await db.save_document(
                notice_id=None, user_id=None,
                filename=stored.filename, content_type=ct, size_bytes=len(data),
            )
        except Exception:
            pass  # non-fatal

        results.append({
            "file_id": stored.file_id,
            "filename": stored.filename,
            "content_type": stored.content_type,
            "size": stored.size,
        })

    return {"files": results}


@app.delete("/documents/{file_id}")
async def delete_document(file_id: str):
    """Remove an uploaded document."""
    if not upload_store.delete(file_id):
        raise HTTPException(status_code=404, detail="File not found")
    return {"ok": True}


@app.get("/pricing")
async def pricing():
    """Return the two service tiers and their pricing."""
    return {
        "tiers": [
            {
                "id": "self_send",
                "name": "Self-Send",
                "price_inr": 199,
                "description": (
                    "AI-generated legal notice with full statutory argumentation, T&C counter-arguments, "
                    "and professional PDF. Emailed to you for self-dispatch via email."
                ),
                "includes": [
                    "Professional PDF legal notice",
                    "Statutory section citations with bare-act text",
                    "T&C counter-arguments (preemptive defense rebuttal)",
                    "Limitation, jurisdiction, and arbitration analysis",
                    "Proof-of-service guidance",
                    "Emailed to your inbox — you send it to the company",
                ],
            },
            {
                "id": "lawyer",
                "name": "Lawyer-Assisted",
                "price_inr": 599,
                "description": (
                    "Everything in Self-Send, PLUS reviewed and attested by a licensed advocate. "
                    "Notice served directly to the company via email on advocate's letterhead, "
                    "with read-receipt tracking."
                ),
                "includes": [
                    "Everything in Self-Send",
                    "Advocate review and attestation",
                    "Sent to the company on your behalf from advocate's verified email",
                    "Read-receipt tracking for proof of electronic service",
                    "Advocate attestation block on the PDF",
                ],
            },
        ]
    }


@app.post("/notice/typed")
async def create_notice_typed(payload: NoticeRequest):
    try:
        complaint = ComplaintInput(
            mode=IntakeMode.typed,
            complainant=payload.complainant,
            company_name_hint=payload.company_name_hint,
            website=payload.website,
            issue_summary=payload.issue_summary,
            timeline=payload.timeline,
            evidence=payload.evidence,
            desired_resolution=payload.desired_resolution,
            jurisdiction=payload.jurisdiction,
        )

        # ── Block criminal / individual-vs-individual cases ──────
        case_type, _ = await pipeline._classify_case(
            payload.issue_summary, payload.company_name_hint,
        )
        if case_type in ("criminal", "individual_dispute"):
            label = "criminal matter" if case_type == "criminal" else "individual-vs-individual dispute"
            raise HTTPException(
                status_code=422,
                detail=(
                    f"This appears to be a {label}. Lawly only generates consumer legal notices "
                    "against companies. Please consult a qualified lawyer for this type of matter."
                ),
            )

        # Analyze uploaded documents if any
        doc_analysis = None
        if payload.upload_ids:
            files = upload_store.get_many(payload.upload_ids)
            if files:
                from legaltech.services.document_analyzer import analyze_documents
                doc_analysis = await analyze_documents(pipeline.llm, files)

        packet = await pipeline.run(
            complaint,
            tier=payload.tier,
            follow_up_answers=payload.follow_up_answers,
            customer_controls={
                "notice_tone": payload.notice_tone,
                "cure_period_days": payload.cure_period_days,
                "compensation_amount": payload.compensation_amount,
                "interest_rate_percent": payload.interest_rate_percent,
                "language": payload.language,
            },
            document_analysis=doc_analysis,
        )
        result = packet.model_dump()
        company_label = packet.company.legal_name or packet.company.brand_name or payload.company_name_hint or "Unknown"
        tier_val = payload.tier.value if hasattr(payload.tier, "value") else str(payload.tier)
        notice_id = notice_store.save_notice(
            complainant_name=payload.complainant.full_name,
            complainant_email=payload.complainant.email,
            company_name=company_label,
            tier=tier_val,
            legal_notice=packet.legal_notice,
        )
        result["notice_id"] = notice_id

        # ── Persist to database ──────────────────────────────────
        try:
            user_id = await db.upsert_user(
                full_name=payload.complainant.full_name,
                email=payload.complainant.email,
                phone=getattr(payload.complainant, "phone", None),
                address=getattr(payload.complainant, "address", None),
            )
            db_notice_id = await db.save_notice_full(
                user_id=user_id,
                company_name=company_label,
                tier=tier_val,
                packet=result,
                customer_controls={
                    "notice_tone": payload.notice_tone,
                    "cure_period_days": payload.cure_period_days,
                    "compensation_amount": payload.compensation_amount,
                    "interest_rate_percent": payload.interest_rate_percent,
                    "language": payload.language,
                },
                follow_up_answers=payload.follow_up_answers,
            )
            result["db_notice_id"] = db_notice_id
            result["db_user_id"] = user_id
            # Store generated PDF
            is_lawyer = tier_val == "lawyer"
            pdf_bytes = generate_pdf(packet.legal_notice, is_lawyer_tier=is_lawyer)
            pdf_fn = f"Legal_Notice_{company_label.replace(' ', '_')}.pdf"
            await db.store_pdf(db_notice_id, pdf_bytes, pdf_fn)
        except Exception:
            import logging
            logging.getLogger(__name__).warning("DB save failed (non-fatal)", exc_info=True)

        # ── Track analytics event ────────────────────────────────
        try:
            notice_store.track_event("notice_generated", {
                "notice_id": notice_id,
                "tier": tier_val,
                "company": company_label,
                "category": getattr(packet, "category", "") or "",
            })
        except Exception:
            pass

        return result
    except Exception as exc:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.") from exc


@app.post("/notice/analyze")
async def analyze_case(payload: AnalyzeRequest):
    """Phase 1: Analyze the complaint and return follow-up questions.

    Call this BEFORE /notice/typed. If ready_to_generate is False,
    present the questions to the user, collect answers, and call
    /notice/analyze again with previous_answers until ready.
    """
    try:
        raw_complainant = payload.complainant
        if isinstance(raw_complainant, Complainant):
            analyze_complainant = raw_complainant
        elif isinstance(raw_complainant, dict):
            name = (raw_complainant.get("full_name") or "").strip()
            email = (raw_complainant.get("email") or "").strip()
            analyze_complainant = Complainant(
                full_name=name or "Pending Customer",
                email=email or "pending@lawly.store",
                phone=(raw_complainant.get("phone") or None),
                address=(raw_complainant.get("address") or "India"),
            )
        else:
            analyze_complainant = Complainant(
                full_name="Pending Customer",
                email="pending@lawly.store",
                address="India",
            )

        complaint = ComplaintInput(
            mode=IntakeMode.typed,
            complainant=analyze_complainant,
            company_name_hint=payload.company_name_hint,
            website=payload.website,
            issue_summary=payload.issue_summary,
            timeline=payload.timeline,
            evidence=payload.evidence,
            desired_resolution=payload.desired_resolution,
            jurisdiction=payload.jurisdiction,
        )
        # Analyze uploaded documents if any
        doc_analysis = None
        if payload.upload_ids:
            files = upload_store.get_many(payload.upload_ids)
            if files:
                from legaltech.services.document_analyzer import analyze_documents
                doc_analysis = await analyze_documents(pipeline.llm, files)

        result = await pipeline.analyze(
            complaint,
            previous_answers=payload.previous_answers,
            document_analysis=doc_analysis,
        )
        result_dict = result.model_dump()

        # ── Persist analysis to database ─────────────────────────
        try:
            user_id = None
            if analyze_complainant.email and analyze_complainant.email != "pending@lawly.store":
                user_id = await db.upsert_user(
                    full_name=analyze_complainant.full_name,
                    email=analyze_complainant.email,
                    phone=getattr(analyze_complainant, "phone", None),
                    address=getattr(analyze_complainant, "address", None),
                )
            analysis_id = await db.save_analysis(
                user_id=user_id,
                complaint=complaint.model_dump(),
                result=result_dict,
            )
            result_dict["db_analysis_id"] = analysis_id
        except Exception:
            import logging
            logging.getLogger(__name__).warning("DB analysis save failed (non-fatal)", exc_info=True)

        return result_dict
    except Exception as exc:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.") from exc


@app.get("/notice/cost")
async def notice_cost():
    """Return the LLM cost breakdown per generation."""
    return pipeline.llm.pricing_info


@app.post("/notice/voice")
async def create_notice_voice(payload: VoiceNoticeRequest):
    try:
        complaint = ComplaintInput(
            mode=IntakeMode.voice,
            complainant=payload.complainant,
            company_name_hint=payload.company_name_hint,
            website=payload.website,
            issue_summary=payload.issue_summary,
            transcript_text=payload.transcript_text,
            timeline=payload.timeline,
            evidence=payload.evidence,
            desired_resolution=payload.desired_resolution,
            jurisdiction=payload.jurisdiction,
        )
        packet = await pipeline.run(
            complaint,
            tier=payload.tier,
            follow_up_answers=payload.follow_up_answers,
            customer_controls={
                "notice_tone": payload.notice_tone,
                "cure_period_days": payload.cure_period_days,
                "compensation_amount": payload.compensation_amount,
                "interest_rate_percent": payload.interest_rate_percent,
                "language": payload.language,
            },
        )
        result = packet.model_dump()

        # ── Persist to database ──────────────────────────────────
        try:
            user_id = await db.upsert_user(
                full_name=payload.complainant.full_name,
                email=payload.complainant.email,
                phone=getattr(payload.complainant, "phone", None),
                address=getattr(payload.complainant, "address", None),
            )
            tier_val = payload.tier.value if hasattr(payload.tier, "value") else str(payload.tier)
            company_label = packet.company.legal_name or packet.company.brand_name or payload.company_name_hint or "Unknown"
            db_nid = await db.save_notice_full(
                user_id=user_id,
                company_name=company_label,
                tier=tier_val,
                packet=result,
                follow_up_answers=payload.follow_up_answers,
            )
            result["db_notice_id"] = db_nid
            result["db_user_id"] = user_id
            # Store generated PDF
            is_lawyer = tier_val == "lawyer"
            pdf_bytes = generate_pdf(packet.legal_notice, is_lawyer_tier=is_lawyer)
            pdf_fn = f"Legal_Notice_{company_label.replace(' ', '_')}.pdf"
            await db.store_pdf(db_nid, pdf_bytes, pdf_fn)
        except Exception:
            import logging
            logging.getLogger(__name__).warning("DB save failed (non-fatal)", exc_info=True)

        return result
    except Exception as exc:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.") from exc


@app.post("/translate/to-english")
async def translate_to_english(payload: TranslateRequest):
    source = payload.text.strip()
    if not source:
        return {"translated_text": ""}

    try:
        translated = await pipeline.llm_fast.complete_text(
            system_prompt=(
                "You are a precise translation engine for Indian consumer complaints. "
                "Translate Hindi/English mixed text to clear professional English. "
                "Do not add or remove facts. Preserve names, amounts, dates, order IDs, and product details."
            ),
            user_prompt=f"Translate this to English only:\n\n{source}",
            max_tokens=1500,
        )
        return {"translated_text": translated.strip()}
    except Exception as exc:
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.") from exc


@app.post("/intake/from-transcript")
async def intake_from_transcript(payload: TranscriptIntakeRequest):
    source = payload.transcript_text.strip()
    if not source:
        raise HTTPException(status_code=400, detail="Transcript is empty")

    try:
        extraction = await pipeline.llm_fast.complete_json(
            system_prompt=(
                "You extract Indian consumer complaint facts from a spoken transcript. "
                "Return strict JSON with keys: issue_summary (string), desired_resolution (string), "
                "timeline (array of short strings), evidence (array of short strings), "
                "company_name_hint (string|null), website (string|null), inferred_facts (object). "
                "Translate Hindi mixed content to clean English. Keep all monetary values, dates, order IDs, "
                "ticket numbers, and names exact. Never invent facts."
            ),
            user_prompt=f"Transcript:\n{source}",
            max_tokens=2500,
        )

        issue_summary = (extraction.get("issue_summary") or source).strip()
        desired_resolution = (
            (extraction.get("desired_resolution") or payload.desired_resolution or "Compensate and resolve the grievance")
            .strip()
        )
        timeline = [x.strip() for x in extraction.get("timeline", []) if isinstance(x, str) and x.strip()]
        evidence = [x.strip() for x in extraction.get("evidence", []) if isinstance(x, str) and x.strip()]

        merged_timeline = [*payload.timeline, *timeline]
        merged_evidence = [*payload.evidence, *evidence]

        complaint = ComplaintInput(
            mode=IntakeMode.voice,
            complainant=payload.complainant,
            company_name_hint=(extraction.get("company_name_hint") or payload.company_name_hint),
            website=(extraction.get("website") or payload.website),
            issue_summary=issue_summary,
            timeline=merged_timeline,
            evidence=merged_evidence,
            desired_resolution=desired_resolution,
            jurisdiction=payload.jurisdiction,
            transcript_text=source,
        )

        first = await pipeline.analyze(complaint, previous_answers=None)

        auto_answers: dict[str, str] = {}
        if first.questions:
            q_payload = [
                {
                    "id": q.id,
                    "question": q.question,
                    "why_it_matters": q.why_it_matters,
                }
                for q in first.questions
            ]
            answer_obj = await pipeline.llm_fast.complete_json(
                system_prompt=(
                    "You answer follow-up legal intake questions ONLY from provided transcript/facts. "
                    "Return strict JSON object: {\"answers\": {question_id: answer_or_empty}}. "
                    "If answer is not supported, return empty string for that id."
                ),
                user_prompt=(
                    f"Transcript:\n{source}\n\n"
                    f"Extracted issue summary:\n{issue_summary}\n\n"
                    f"Extracted timeline:\n{merged_timeline}\n\n"
                    f"Extracted evidence:\n{merged_evidence}\n\n"
                    f"Questions:\n{q_payload}"
                ),
                max_tokens=2000,
            )

            raw_answers = answer_obj.get("answers", {}) if isinstance(answer_obj, dict) else {}
            for q in first.questions:
                val = (raw_answers.get(q.id) or "").strip() if isinstance(raw_answers, dict) else ""
                if val:
                    auto_answers[q.id] = val

        final_analysis = first
        if auto_answers:
            final_analysis = await pipeline.analyze(complaint, previous_answers=auto_answers)

        return {
            "issue_summary": issue_summary,
            "desired_resolution": desired_resolution,
            "timeline": merged_timeline,
            "evidence": merged_evidence,
            "company_name_hint": complaint.company_name_hint,
            "website": str(complaint.website) if complaint.website else None,
            "auto_answers": auto_answers,
            "analysis": final_analysis.model_dump(),
        }
    except Exception as exc:
        logger.exception("Transcript intake failed")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.") from exc


@app.post("/speech/refine")
async def refine_speech_transcript(payload: SpeechRefineRequest):
    text = payload.transcript_text.strip()
    if not text:
        return {
            "romanized_text": "",
            "english_text": "",
            "quality_note": "empty_input",
        }

    try:
        refined = await pipeline.llm_fast.complete_json(
            system_prompt=(
                "You are an ASR post-processor for Indian Hinglish consumer complaints. "
                "Input may contain Hindi words, English words, misspellings, and mixed scripts. "
                "Return strict JSON with keys: romanized_text, english_text, quality_note. "
                "romanized_text: keep meaning intact, render everything in English script (Latin letters), "
                "including Hindi words transliterated. "
                "english_text: accurate English translation preserving all facts, dates, amounts, IDs. "
                "Do not invent facts."
            ),
            user_prompt=f"Raw transcript:\n{text}",
            max_tokens=1800,
        )
        return {
            "romanized_text": (refined.get("romanized_text") or text).strip(),
            "english_text": (refined.get("english_text") or text).strip(),
            "quality_note": (refined.get("quality_note") or "ok").strip(),
        }
    except Exception as exc:
        # Fallback: preserve original transcript so UX doesn't break.
        return {
            "romanized_text": text,
            "english_text": text,
            "quality_note": f"fallback: {exc}",
        }


@app.post("/notice/typed/pdf")
async def create_notice_typed_pdf(payload: NoticeRequest):
    """Generate and return the PDF file directly (for download)."""
    try:
        complaint = ComplaintInput(
            mode=IntakeMode.typed,
            complainant=payload.complainant,
            company_name_hint=payload.company_name_hint,
            website=payload.website,
            issue_summary=payload.issue_summary,
            timeline=payload.timeline,
            evidence=payload.evidence,
            desired_resolution=payload.desired_resolution,
            jurisdiction=payload.jurisdiction,
        )
        # Analyze uploaded documents if any
        doc_analysis = None
        if payload.upload_ids:
            files = upload_store.get_many(payload.upload_ids)
            if files:
                from legaltech.services.document_analyzer import analyze_documents
                doc_analysis = await analyze_documents(pipeline.llm, files)

        packet = await pipeline.run(
            complaint,
            tier=payload.tier,
            follow_up_answers=payload.follow_up_answers,
            customer_controls={
                "notice_tone": payload.notice_tone,
                "cure_period_days": payload.cure_period_days,
                "compensation_amount": payload.compensation_amount,
                "interest_rate_percent": payload.interest_rate_percent,
                "language": payload.language,
            },
            document_analysis=doc_analysis,
        )
        is_lawyer = payload.tier == ServiceTier.lawyer_assisted
        annexures = [
            (sf.filename, sf.content_type, sf.data)
            for sf in upload_store.get_many(payload.upload_ids)
        ] if payload.upload_ids else []
        pdf_bytes = generate_pdf(packet.legal_notice, is_lawyer_tier=is_lawyer, annexures=annexures)
        company_label = packet.company.legal_name or packet.company.brand_name or "Company"
        filename = f"Legal_Notice_{company_label.replace(' ', '_')}.pdf"

        # ── Persist to database ──────────────────────────────────────
        try:
            user_id = await db.upsert_user(
                full_name=payload.complainant.full_name,
                email=payload.complainant.email,
                phone=getattr(payload.complainant, "phone", None),
                address=getattr(payload.complainant, "address", None),
            )
            tier_val = payload.tier.value if hasattr(payload.tier, "value") else str(payload.tier)
            db_nid = await db.save_notice_full(
                user_id=user_id,
                company_name=company_label,
                tier=tier_val,
                packet=packet.model_dump(),
                customer_controls={
                    "notice_tone": payload.notice_tone,
                    "cure_period_days": payload.cure_period_days,
                    "compensation_amount": payload.compensation_amount,
                    "interest_rate_percent": payload.interest_rate_percent,
                    "language": payload.language,
                },
                follow_up_answers=payload.follow_up_answers,
            )
            # Store the generated PDF
            await db.store_pdf(db_nid, pdf_bytes, filename)
        except Exception:
            import logging
            logging.getLogger(__name__).warning("DB save failed (non-fatal)", exc_info=True)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.") from exc


# ── Root redirect ────────────────────────────────────────────────────


class RenderPDFRequest(BaseModel):
    notice_text: str
    company_name: str = "Company"
    is_lawyer_tier: bool = False



@app.post("/notice/deliver")
async def deliver_notice(payload: RenderPDFRequest, to_email: str = Query(...), to_name: str = Query(...)):
    """Deliver already-generated notice via email."""
    if not payload.notice_text or not payload.notice_text.strip():
        raise HTTPException(status_code=400, detail="notice_text is required")
        
    try:
        from .services.pdf_generator import generate_pdf
        from .services.email_service import send_notice_email, build_self_send_body, build_lawyer_send_body
        
        pdf_bytes = generate_pdf(
            payload.notice_text,
            is_lawyer_tier=payload.is_lawyer_tier,
        )
        filename = f"Legal_Notice_{payload.company_name.replace(' ', '_')}.pdf"
        
        if payload.is_lawyer_tier:
            body = build_lawyer_send_body(to_name, payload.company_name, "")
            subject = f"Legal Notice on behalf of {to_name} v. {payload.company_name}"
        else:
            body = build_self_send_body(to_name, payload.company_name)
            subject = f"Your Legal Notice against {payload.company_name}"
            
        result = send_notice_email(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            body_text=body,
            pdf_bytes=pdf_bytes,
            pdf_filename=filename
        )
        
        return {"success": True, "delivered_to": to_email, "email_status": result.success, "message": result.message}
    except Exception as exc:
        logger.exception("PDF generation and delivery failed")
        raise HTTPException(status_code=500, detail="An internal error occurred during delivery.") from exc

@app.post("/notice/render-pdf")
async def render_pdf(payload: RenderPDFRequest):
    """Convert already-generated notice text into a PDF (no pipeline re-run)."""
    if not payload.notice_text or not payload.notice_text.strip():
        raise HTTPException(status_code=400, detail="notice_text is required")
    try:
        pdf_bytes = generate_pdf(
            payload.notice_text,
            is_lawyer_tier=payload.is_lawyer_tier,
        )
        filename = f"Legal_Notice_{payload.company_name.replace(' ', '_')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.exception("PDF rendering failed")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.") from exc


@app.get("/")
async def root():
    """Serve index.html with injected FAQ schema and hreflang tags if configured."""
    index_path = _STATIC_DIR / "index.html"
    html_content = index_path.read_text(encoding="utf-8")

    seo = notice_store.get_seo_settings()
    inject = ""

    # FAQ structured data
    faq_items = seo.get("faq_schema", [])
    if faq_items:
        import json as json_mod
        import html as html_mod
        faq_ld = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item.get("question", ""),
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": item.get("answer", ""),
                    },
                }
                for item in faq_items
                if item.get("question") and item.get("answer")
            ],
        }
        inject += f'\n    <script type="application/ld+json">{json_mod.dumps(faq_ld)}</script>'

    # Hreflang tags
    for entry in seo.get("hreflang_entries", []):
        import html as html_mod
        lang = html_mod.escape(entry.get("lang", ""))
        href = html_mod.escape(entry.get("href", ""))
        if lang and href:
            inject += f'\n    <link rel="alternate" hreflang="{lang}" href="{href}">'

    # OG image
    og_image = seo.get("og_image", "")
    if og_image:
        import html as html_mod
        inject += f'\n    <meta property="og:image" content="{html_mod.escape(og_image)}">'

    # Bing verification
    bing = seo.get("bing_verification", "")
    if bing:
        import html as html_mod
        inject += f'\n    <meta name="msvalidate.01" content="{html_mod.escape(bing)}">'

    # AEO: Organization JSON-LD
    aeo = notice_store.get_aeo_settings()
    org = aeo.get("org_schema", {})
    if org.get("name"):
        import json as json_mod
        org_ld = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": org["name"],
            "url": org.get("url", ""),
        }
        if org.get("logo"):
            org_ld["logo"] = org["logo"]
        if org.get("description"):
            org_ld["description"] = org["description"]
        if org.get("founding_date"):
            org_ld["foundingDate"] = org["founding_date"]
        if org.get("contact_email"):
            org_ld["contactPoint"] = {"@type": "ContactPoint", "email": org["contact_email"]}
            if org.get("contact_phone"):
                org_ld["contactPoint"]["telephone"] = org["contact_phone"]
        same_as = [s.get("url", s) if isinstance(s, dict) else s for s in org.get("same_as", []) if s]
        if same_as:
            org_ld["sameAs"] = same_as
        inject += f'\n    <script type="application/ld+json">{json_mod.dumps(org_ld)}</script>'

    # AEO: HowTo schemas
    for howto in aeo.get("howto_schemas", []):
        if howto.get("name") and howto.get("steps"):
            import json as json_mod
            howto_ld = {
                "@context": "https://schema.org",
                "@type": "HowTo",
                "name": howto["name"],
                "step": [
                    {"@type": "HowToStep", "position": i + 1, "text": step}
                    for i, step in enumerate(howto["steps"])
                    if step
                ],
            }
            if howto.get("description"):
                howto_ld["description"] = howto["description"]
            inject += f'\n    <script type="application/ld+json">{json_mod.dumps(howto_ld)}</script>'

    # AEO: Speakable
    speakable_sels = aeo.get("speakable_selectors", [])
    if speakable_sels:
        import json as json_mod
        speak_ld = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "speakable": {
                "@type": "SpeakableSpecification",
                "cssSelector": speakable_sels,
            },
        }
        inject += f'\n    <script type="application/ld+json">{json_mod.dumps(speak_ld)}</script>'

    if inject:
        html_content = html_content.replace("</head>", f"{inject}\n</head>", 1)

    return HTMLResponse(content=html_content)


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(str(_STATIC_DIR / "favicon.ico"))


@app.get("/style.css")
async def style_css():
    return FileResponse(str(_STATIC_DIR / "style.css"))


@app.get("/app.js")
async def app_js():
    return FileResponse(str(_STATIC_DIR / "app.js"))


@app.get("/img/{asset_path:path}")
async def img_asset(asset_path: str):
    return FileResponse(str(_STATIC_DIR / "img" / asset_path))


@app.get("/admin.html")
async def admin_html_page():
    return FileResponse(str(_STATIC_DIR / "admin.html"))


@app.get("/admin")
async def admin_page():
    return FileResponse(str(_STATIC_DIR / "admin.html"))


# ── Admin API ────────────────────────────────────────────────────────

class LawyerDetails(BaseModel):
    name: str
    email: str
    phone: str | None = None
    enrollment_no: str
    bar_council: str | None = None


class NoticeStatusUpdate(BaseModel):
    status: str  # "approved", "sent", "rejected"
    reviewer_notes: str | None = None


@app.get("/api/admin/stats")
async def get_dashboard_stats(_=Depends(require_admin)):
    # Merge JSON-file stats with DB stats
    json_stats = notice_store.get_dashboard_stats()
    try:
        db_stats = await db.get_dashboard_stats_db()
        json_stats["db_total_users"] = db_stats.get("total_users", 0)
        json_stats["db_total_analyses"] = db_stats.get("total_analyses", 0)
        json_stats["db_total_notices"] = db_stats.get("total_notices", 0)
    except Exception:
        pass
    return json_stats


@app.get("/api/admin/activity")
async def get_activity_log(limit: int = 50, _=Depends(require_admin)):
    return notice_store.get_activity_log(limit)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@app.put("/api/admin/password")
async def change_admin_password(body: ChangePasswordRequest, _=Depends(require_admin)):
    settings = get_settings()
    stored_pw = notice_store.get_stored_password()
    expected = stored_pw if stored_pw else settings.admin_password
    if not hmac.compare_digest(body.current_password, expected):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    notice_store.set_stored_password(body.new_password)
    notice_store.log_activity("Changed admin password", "", "auth")
    return {"ok": True}


@app.get("/api/admin/lawyer")
async def get_lawyer(_=Depends(require_admin)):
    data = notice_store.get_lawyer()
    return data or {}


@app.put("/api/admin/lawyer")
async def save_lawyer(details: LawyerDetails, _=Depends(require_admin)):
    result = notice_store.save_lawyer(details.model_dump())
    notice_store.log_activity("Updated lawyer details", f"Lawyer: {details.name}", "lawyer")
    return result


@app.get("/api/admin/notices")
async def get_notices(_=Depends(require_admin)):
    return notice_store.get_all_notices()


@app.get("/api/admin/notices/{notice_id}")
async def get_notice_detail(notice_id: str, _=Depends(require_admin)):
    notice = notice_store.get_notice(notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return notice


@app.put("/api/admin/notices/{notice_id}/status")
async def update_notice_status(notice_id: str, body: NoticeStatusUpdate, _=Depends(require_admin)):
    result = notice_store.update_notice_status(notice_id, body.status, body.reviewer_notes)
    if not result:
        raise HTTPException(status_code=404, detail="Notice not found")
    notice_store.log_activity(
        f"Notice {body.status}",
        body.reviewer_notes or "",
        "notice",
        notice_id,
    )
    return result


@app.get("/api/admin/notices/{notice_id}/pdf")
async def get_notice_pdf(notice_id: str, _=Depends(require_admin)):
    notice = notice_store.get_notice(notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    is_lawyer = notice.get("tier") == "lawyer"
    pdf_bytes = generate_pdf(notice["legal_notice"], is_lawyer_tier=is_lawyer)
    filename = f"Legal_Notice_{notice_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── SEO Settings API ────────────────────────────────────────────────

class SEOSettingsUpdate(BaseModel):
    site_title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    canonical_url: str | None = None
    google_analytics_id: str | None = None
    google_search_console_verification: str | None = None
    bing_verification: str | None = None
    custom_head_tags: str | None = None
    default_robots: str | None = None
    hreflang_entries: list[dict] | None = None
    faq_schema: list[dict] | None = None


@app.get("/api/admin/seo")
async def get_seo(_=Depends(require_admin)):
    return notice_store.get_seo_settings()


@app.put("/api/admin/seo")
async def save_seo(body: SEOSettingsUpdate, _=Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    result = notice_store.save_seo_settings(data)
    notice_store.log_activity("Updated SEO settings", "", "seo")
    return result


# ── SEO Audit ────────────────────────────────────────────────────────

@app.get("/api/admin/seo/audit")
async def seo_audit(_=Depends(require_admin)):
    """Run an automated SEO health check and return a scored report."""
    seo = notice_store.get_seo_settings()
    pages = notice_store.get_all_pages()
    blog_posts = notice_store.get_all_blog_posts()
    published = [p for p in blog_posts if p.get("status") == "published"]

    checks: list[dict] = []
    score = 0
    total = 0

    def check(name: str, passed: bool, tip: str, weight: int = 1):
        nonlocal score, total
        total += weight
        if passed:
            score += weight
        checks.append({"name": name, "passed": passed, "tip": tip, "weight": weight})

    title = seo.get("site_title", "")
    desc = seo.get("meta_description", "")
    keywords = seo.get("meta_keywords", "")
    canonical = seo.get("canonical_url", "")

    # Core meta
    check("Title length (50-60 chars)", 50 <= len(title) <= 60,
          f"Currently {len(title)} chars. Aim for 50-60 for best SERP display.", 2)
    check("Meta description (120-160 chars)", 120 <= len(desc) <= 160,
          f"Currently {len(desc)} chars. Aim for 120-160.", 2)
    check("Keywords defined", len(keywords) > 0,
          "Add target keywords for density tracking.", 1)
    check("Canonical URL set", len(canonical) > 4,
          "Set a canonical URL to prevent duplicate content issues.", 2)

    # OG tags
    check("OG title set", bool(seo.get("og_title")),
          "Set OG title for better social sharing.", 1)
    check("OG description set", bool(seo.get("og_description")),
          "Set OG description for better social sharing.", 1)
    check("OG image set", bool(seo.get("og_image")),
          "Add an OG image (1200x630px recommended) for social cards.", 2)

    # Verification
    check("Google Search Console verified", bool(seo.get("google_search_console_verification")),
          "Verify with Google Search Console for indexing insights.", 2)
    check("Google Analytics configured", bool(seo.get("google_analytics_id")),
          "Add GA ID to track organic traffic.", 1)
    check("Bing Webmaster verified", bool(seo.get("bing_verification")),
          "Verify with Bing Webmaster Tools for additional search coverage.", 1)

    # Content
    check("Blog posts published (3+)", len(published) >= 3,
          f"You have {len(published)} published posts. Aim for 3+ to build topical authority.", 2)
    check("Blog posts with meta descriptions", all(p.get("meta_description") for p in published),
          "Ensure every published blog post has a meta description.", 2)
    check("Blog posts with keywords", all(p.get("meta_keywords") for p in published),
          "Add meta keywords to each blog post.", 1)

    # Sitemap
    check("Sitemap has pages", len(pages) >= 1,
          "Add PAGES to your sitemap for better crawl coverage.", 1)

    # Structured data
    check("FAQ schema configured", len(seo.get("faq_schema", [])) > 0,
          "Add FAQ schema — FAQs can appear as rich snippets in search results.", 2)

    # Hreflang
    check("Hreflang for Hindi audience", len(seo.get("hreflang_entries", [])) > 0,
          "Add hreflang entries (en-IN, hi-IN) to target Hindi + English searchers.", 1)

    # Redirects
    redirects = notice_store.get_all_redirects()
    check("301 redirects managed", True, "Redirect manager is available.", 0)

    pct = round((score / total) * 100) if total > 0 else 0
    grade = "A" if pct >= 90 else "B" if pct >= 75 else "C" if pct >= 60 else "D" if pct >= 40 else "F"

    return {
        "score": pct,
        "grade": grade,
        "total_checks": len(checks),
        "passed": sum(1 for c in checks if c["passed"]),
        "failed": sum(1 for c in checks if not c["passed"]),
        "checks": checks,
        "summary": {
            "published_posts": len(published),
            "total_pages": len(pages),
            "total_redirects": len(redirects),
        },
    }


# ── 301 Redirects API ───────────────────────────────────────────────

class RedirectInput(BaseModel):
    from_path: str
    to_path: str
    status_code: int = 301

@app.get("/api/admin/redirects")
async def list_redirects(_=Depends(require_admin)):
    return notice_store.get_all_redirects()

@app.post("/api/admin/redirects")
async def create_redirect(body: RedirectInput, _=Depends(require_admin)):
    entry = body.model_dump()
    result = notice_store.save_redirect(entry)
    notice_store.log_activity("Created redirect", f"{body.from_path} → {body.to_path}", "seo")
    return result

@app.delete("/api/admin/redirects/{redirect_id}")
async def delete_redirect(redirect_id: str, _=Depends(require_admin)):
    if not notice_store.delete_redirect(redirect_id):
        raise HTTPException(status_code=404, detail="Redirect not found")
    notice_store.log_activity("Deleted redirect", redirect_id, "seo")
    return {"ok": True}


# ── Sitemap Ping ─────────────────────────────────────────────────────

@app.post("/api/admin/seo/ping-sitemap")
async def ping_sitemap(_=Depends(require_admin)):
    """Notify Google and Bing that the sitemap has been updated."""
    import httpx
    seo = notice_store.get_seo_settings()
    base = seo.get("canonical_url", "https://lawly.store/").rstrip("/")
    sitemap_url = f"{base}/sitemap.xml"
    results = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for name, ping_url in [
            ("google", f"https://www.google.com/ping?sitemap={sitemap_url}"),
            ("bing", f"https://www.bing.com/ping?sitemap={sitemap_url}"),
        ]:
            try:
                resp = await client.get(ping_url)
                results[name] = {"status": resp.status_code, "ok": resp.status_code < 400}
            except Exception as e:
                results[name] = {"status": 0, "ok": False, "error": str(e)}
    notice_store.log_activity("Pinged search engines", f"Sitemap: {sitemap_url}", "seo")
    return results


# ── AEO / AI Engine Optimization ─────────────────────────────────────

class AEOSettingsUpdate(BaseModel):
    llms_txt: str | None = None
    llms_full_txt: str | None = None
    org_schema: dict | None = None
    speakable_selectors: list[str] | None = None
    howto_schemas: list[dict] | None = None
    ai_snippets: list[dict] | None = None
    topic_clusters: list[dict] | None = None
    cite_sources: list[dict] | None = None


@app.get("/api/admin/aeo")
async def get_aeo(_=Depends(require_admin)):
    return notice_store.get_aeo_settings()


@app.put("/api/admin/aeo")
async def save_aeo(body: AEOSettingsUpdate, _=Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    result = notice_store.save_aeo_settings(data)
    notice_store.log_activity("Updated AEO settings", "", "aeo")
    return result


@app.get("/api/admin/aeo/audit")
async def aeo_audit(_=Depends(require_admin)):
    """Run an AI Engine Optimization health audit."""
    import html as html_mod
    aeo = notice_store.get_aeo_settings()
    seo = notice_store.get_seo_settings()
    posts = notice_store.get_published_blog_posts()

    checks: list[dict] = []

    def _check(name: str, passed: bool, tip: str, weight: int = 1):
        checks.append({"name": name, "passed": passed, "tip": tip, "weight": weight})

    # 1. llms.txt configured
    llms = (aeo.get("llms_txt") or "").strip()
    _check("llms.txt configured", bool(llms), "Create a llms.txt file so AI crawlers understand your site purpose and offerings.", 3)

    # 2. llms-full.txt configured
    llms_full = (aeo.get("llms_full_txt") or "").strip()
    _check("llms-full.txt configured", bool(llms_full), "Provide comprehensive content in llms-full.txt for deeper AI understanding.", 2)

    # 3. Organization schema complete
    org = aeo.get("org_schema", {})
    org_fields = ["name", "url", "logo", "description"]
    org_filled = sum(1 for f in org_fields if org.get(f))
    _check("Organization schema complete", org_filled >= 3, f"{org_filled}/{len(org_fields)} core fields filled. Add name, URL, logo, description.", 2)

    # 4. sameAs links (social profiles / Wikipedia)
    same_as = org.get("same_as", [])
    _check("Social/sameAs links", len(same_as) >= 2, "Add social profiles, Wikipedia, Crunchbase links so AI knows your brand identity.", 2)

    # 5. FAQ schema (already in SEO)
    faq = seo.get("faq_schema", [])
    _check("FAQ schema for AI answers", len(faq) >= 3, f"{len(faq)} FAQ items. Add 3+ question-answer pairs — AI engines love extracting these.", 3)

    # 6. HowTo schemas
    howtos = aeo.get("howto_schemas", [])
    _check("HowTo schemas defined", len(howtos) >= 1, "Create step-by-step HowTo guides — AI assistants prominently feature these.", 2)

    # 7. AI-ready content snippets
    snippets = aeo.get("ai_snippets", [])
    _check("AI answer snippets", len(snippets) >= 3, f"{len(snippets)} snippets. Write 3+ concise authoritative answers for common queries.", 3)

    # 8. Topic authority clusters
    clusters = aeo.get("topic_clusters", [])
    _check("Topic authority clusters", len(clusters) >= 2, "Define topic clusters to demonstrate expertise depth to AI rankers.", 2)

    # 9. Citation sources
    sources = aeo.get("cite_sources", [])
    _check("Citation sources listed", len(sources) >= 2, "Add authoritative sources you cite — boosts credibility with AI engines.", 1)

    # 10. Speakable selectors
    speakable = aeo.get("speakable_selectors", [])
    _check("Speakable content marked", len(speakable) >= 1, "Mark key content as speakable for voice assistants (Google Assistant, Alexa).", 1)

    # 11. Blog has structured Q&A patterns
    qa_posts = sum(1 for p in posts if any(q in (p.get("title") or "").lower() for q in ["how", "what", "why", "can i", "guide", "step"]))
    _check("Blog has Q&A-style content", qa_posts >= 2, f"{qa_posts} posts with question-style titles. AI engines prioritize conversational Q&A content.", 2)

    # 12. Meta descriptions under 160 chars (AI snippet-friendly)
    good_desc = sum(1 for p in posts if 50 <= len(p.get("meta_description") or "") <= 160)
    _check("Blog meta descs AI-ready", good_desc >= len(posts) * 0.7 or good_desc >= 3, f"{good_desc}/{len(posts)} blog posts have concise meta descriptions (50-160 chars).", 1)

    # 13. Content freshness (posts in last 60 days)
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(days=60)).isoformat()
    recent = sum(1 for p in posts if (p.get("updated_at") or p.get("created_at", "")) > cutoff)
    _check("Content freshness", recent >= 1, f"{recent} posts updated in last 60 days. Fresh content signals authority to AI.", 2)

    # 14. Structured data breadth
    has_org = org_filled >= 3
    has_faq = len(faq) >= 1
    has_howto = len(howtos) >= 1
    schema_count = sum([has_org, has_faq, has_howto])
    _check("Schema diversity (3+ types)", schema_count >= 3, f"{schema_count}/3 schema types. Use Organization + FAQ + HowTo for maximum AI coverage.", 2)

    total_weight = sum(c["weight"] for c in checks)
    earned = sum(c["weight"] for c in checks if c["passed"])
    score = round((earned / total_weight) * 100) if total_weight else 0
    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D" if score >= 30 else "F"

    return {
        "score": score,
        "grade": grade,
        "total_checks": len(checks),
        "passed": sum(1 for c in checks if c["passed"]),
        "failed": sum(1 for c in checks if not c["passed"]),
        "checks": checks,
        "summary": {
            "llms_txt_lines": len(llms.splitlines()) if llms else 0,
            "howto_count": len(howtos),
            "snippet_count": len(snippets),
            "topic_clusters": len(clusters),
            "blog_posts": len(posts),
        },
    }


@app.get("/llms.txt")
async def serve_llms_txt():
    """Serve llms.txt for AI crawlers."""
    aeo = notice_store.get_aeo_settings()
    content = aeo.get("llms_txt", "")
    if not content:
        # Auto-generate a sensible default
        seo = notice_store.get_seo_settings()
        content = f"""# {seo.get('site_title', 'Lawly')}

> {seo.get('meta_description', '')}

## About
Lawly is an AI-powered legal notice generator for Indian consumers.
It helps citizens exercise their consumer protection rights under the Consumer Protection Act 2019.

## Key Features
- AI-generated legal notices backed by 15+ Indian consumer statutes
- Three tiers: Self-Send, Professional Review, Lawyer-Drafted
- Instant PDF generation with proper legal formatting

## Contact
Website: {seo.get('canonical_url', 'https://lawly.store')}
"""
    return Response(content=content, media_type="text/plain; charset=utf-8")


@app.get("/llms-full.txt")
async def serve_llms_full_txt():
    """Serve llms-full.txt with comprehensive site content for AI."""
    aeo = notice_store.get_aeo_settings()
    content = aeo.get("llms_full_txt", "")
    if not content:
        # Auto-generate from blog + FAQ + snippets
        seo = notice_store.get_seo_settings()
        posts = notice_store.get_published_blog_posts()
        parts = [f"# {seo.get('site_title', 'Lawly')} — Complete Information\n"]
        parts.append(f"> {seo.get('meta_description', '')}\n")

        faq = seo.get("faq_schema", [])
        if faq:
            parts.append("## Frequently Asked Questions\n")
            for item in faq:
                parts.append(f"**Q: {item.get('question', '')}**")
                parts.append(f"A: {item.get('answer', '')}\n")

        snippets = aeo.get("ai_snippets", [])
        if snippets:
            parts.append("## Key Topics\n")
            for s in snippets:
                parts.append(f"### {s.get('query', '')}")
                parts.append(f"{s.get('answer', '')}\n")

        if posts:
            parts.append("## Published Guides & Articles\n")
            for p in posts[:20]:
                parts.append(f"### {p.get('title', '')}")
                if p.get("meta_description"):
                    parts.append(p["meta_description"])
                parts.append("")

        content = "\n".join(parts)
    return Response(content=content, media_type="text/plain; charset=utf-8")


# ── Blog Posts API ───────────────────────────────────────────────────

class BlogPostInput(BaseModel):
    title: str
    slug: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    content: str = ""
    author: str = "Jago Grahak Jago"
    status: str = "draft"


@app.get("/api/admin/blog")
async def list_blog_posts(_=Depends(require_admin)):
    return notice_store.get_all_blog_posts()


@app.get("/api/admin/blog/{slug}")
async def get_blog_post(slug: str, _=Depends(require_admin)):
    post = notice_store.get_blog_post(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return post


@app.post("/api/admin/blog")
async def create_blog_post(body: BlogPostInput, _=Depends(require_admin)):
    result = notice_store.save_blog_post(body.model_dump())
    notice_store.log_activity("Created blog post", body.title, "blog", result.get("slug", ""))
    return result


@app.put("/api/admin/blog/{slug}")
async def update_blog_post(slug: str, body: BlogPostInput, _=Depends(require_admin)):
    data = body.model_dump()
    data["slug"] = slug
    result = notice_store.save_blog_post(data)
    notice_store.log_activity("Updated blog post", body.title, "blog", slug)
    return result


@app.delete("/api/admin/blog/{slug}")
async def delete_blog_post(slug: str, _=Depends(require_admin)):
    if not notice_store.delete_blog_post(slug):
        raise HTTPException(status_code=404, detail="Blog post not found")
    notice_store.log_activity("Deleted blog post", slug, "blog", slug)
    return {"ok": True}


# ── Pages API ────────────────────────────────────────────────────────

class PageInput(BaseModel):
    path: str
    title: str = ""
    meta_description: str = ""
    meta_keywords: str = ""
    og_title: str = ""
    og_description: str = ""
    priority: float = 0.5
    changefreq: str = "weekly"
    include_in_sitemap: bool = True


@app.get("/api/admin/pages")
async def list_pages(_=Depends(require_admin)):
    return notice_store.get_all_pages()


@app.post("/api/admin/pages")
async def create_page(body: PageInput, _=Depends(require_admin)):
    result = notice_store.save_page(body.model_dump())
    notice_store.log_activity("Created page", body.path, "page", body.path)
    return result


@app.put("/api/admin/pages/{path:path}")
async def update_page(path: str, body: PageInput, _=Depends(require_admin)):
    data = body.model_dump()
    data["path"] = f"/{path}" if not path.startswith("/") else path
    result = notice_store.save_page(data)
    notice_store.log_activity("Updated page", data["path"], "page", data["path"])
    return result


@app.delete("/api/admin/pages/{path:path}")
async def delete_page(path: str, _=Depends(require_admin)):
    key = f"/{path}" if not path.startswith("/") else path
    if not notice_store.delete_page(key):
        raise HTTPException(status_code=404, detail="Page not found")
    notice_store.log_activity("Deleted page", key, "page", key)
    return {"ok": True}


# ── Dynamic Sitemap ──────────────────────────────────────────────────

@app.get("/sitemap.xml")
async def dynamic_sitemap():
    from datetime import date
    seo = notice_store.get_seo_settings()
    base = seo.get("canonical_url", "https://lawly.store/").rstrip("/")
    today = date.today().isoformat()

    urls = []
    # Home page
    urls.append(f'  <url>\n    <loc>{base}/</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>')

    # Custom pages
    for page in notice_store.get_all_pages():
        if not page.get("include_in_sitemap", True):
            continue
        p = page["path"].lstrip("/")
        pri = page.get("priority", 0.5)
        freq = page.get("changefreq", "weekly")
        urls.append(f'  <url>\n    <loc>{base}/{p}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>{freq}</changefreq>\n    <priority>{pri}</priority>\n  </url>')

    # Published blog posts
    for post in notice_store.get_published_blog_posts():
        slug = post["slug"]
        updated = post.get("updated_at", today)[:10]
        urls.append(f'  <url>\n    <loc>{base}/blog/{slug}</loc>\n    <lastmod>{updated}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>')

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(urls) + '\n</urlset>'
    return Response(content=xml, media_type="application/xml")


@app.get("/robots.txt")
async def dynamic_robots():
    seo = notice_store.get_seo_settings()
    base = seo.get("canonical_url", "https://lawly.store/").rstrip("/")
    body = f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /admin.html\n\nSitemap: {base}/sitemap.xml\n"
    return Response(content=body, media_type="text/plain")


# ── Blog rendering (SSR for crawlers) ────────────────────────────────

def _render_blog_html(post: dict, seo: dict) -> str:
    import html as html_mod
    import json as json_mod
    title = html_mod.escape(post.get("title", ""))
    desc = html_mod.escape(post.get("meta_description", ""))
    keywords = html_mod.escape(post.get("meta_keywords", ""))
    author = html_mod.escape(post.get("author", ""))
    content = post.get("content", "")
    date_str = (post.get("updated_at") or post.get("created_at", ""))[:10]
    base = seo.get("canonical_url", "").rstrip("/")
    slug = post.get("slug", "")
    og_image = html_mod.escape(seo.get("og_image", ""))

    # Breadcrumb structured data
    breadcrumb_ld = json_mod.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{base}/blog"},
            {"@type": "ListItem", "position": 3, "name": post.get("title", ""), "item": f"{base}/blog/{slug}"},
        ]
    })

    # Hreflang tags
    hreflang_tags = ""
    for entry in seo.get("hreflang_entries", []):
        lang = html_mod.escape(entry.get("lang", ""))
        href = html_mod.escape(entry.get("href", "").rstrip("/"))
        if lang and href:
            hreflang_tags += f'\n    <link rel="alternate" hreflang="{lang}" href="{href}/blog/{slug}">'

    og_image_tag = f'\n    <meta property="og:image" content="{og_image}">' if og_image else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Jago Grahak Jago</title>
    <meta name="description" content="{desc}">
    <meta name="keywords" content="{keywords}">
    <meta name="author" content="{author}">
    <link rel="canonical" href="{base}/blog/{slug}">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{desc}">
    <meta property="og:url" content="{base}/blog/{slug}">
    <meta property="og:site_name" content="Jago Grahak Jago">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{desc}">{og_image_tag}{hreflang_tags}
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": "{title}",
        "description": "{desc}",
        "author": {{ "@type": "Person", "name": "{author}" }},
        "datePublished": "{post.get('created_at', '')[:10]}",
        "dateModified": "{date_str}",
        "url": "{base}/blog/{slug}"
    }}
    </script>
    <script type="application/ld+json">{breadcrumb_ld}</script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/style.css">
    <style>
        .blog-article {{ max-width: 720px; margin: 32px auto; padding: 36px 32px; background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
        .blog-article h1 {{ font-size: 2rem; margin-bottom: 8px; color: #111827; }}
        .blog-meta {{ color: #9CA3AF; font-size: .85rem; margin-bottom: 24px; }}
        .blog-content {{ line-height: 1.8; color: #374151; }}
        .blog-content h2 {{ font-size: 1.4rem; margin-top: 28px; margin-bottom: 10px; }}
        .blog-content h3 {{ font-size: 1.15rem; margin-top: 22px; margin-bottom: 8px; }}
        .blog-content p {{ margin-bottom: 14px; }}
        .blog-content ul, .blog-content ol {{ margin-bottom: 14px; padding-left: 24px; }}
        .blog-content li {{ margin-bottom: 6px; }}
        .blog-content a {{ color: #DC2626; }}
        .blog-nav {{ max-width: 720px; margin: 0 auto; padding: 16px 32px; }}
        .blog-nav a {{ color: #DC2626; text-decoration: none; font-weight: 600; }}
        .blog-cta {{ margin-top: 32px; padding: 20px; background: #FFF8E1; border-radius: 12px; border-left: 4px solid #F59E0B; text-align: center; }}
        .blog-cta a {{ color: #DC2626; font-weight: 700; }}
    </style>
</head>
<body>
    <nav class="blog-nav"><a href="/">\u2190 Back to Jago Grahak Jago</a> &nbsp;|&nbsp; <a href="/blog">All Articles</a></nav>
    <article class="blog-article">
        <h1>{title}</h1>
        <div class="blog-meta">By {author} &middot; {date_str}</div>
        <div class="blog-content">{content}</div>
        <div class="blog-cta">
            <p><strong>Need to send a legal notice?</strong></p>
            <p><a href="/">Generate your AI-powered legal notice in minutes \u2192</a></p>
        </div>
    </article>
</body>
</html>"""


def _render_blog_index(posts: list[dict], seo: dict) -> str:
    import html
    base = seo.get("canonical_url", "").rstrip("/")
    items = ""
    for p in posts:
        title = html.escape(p.get("title", ""))
        desc = html.escape(p.get("meta_description", ""))
        slug = p.get("slug", "")
        date_str = (p.get("updated_at") or p.get("created_at", ""))[:10]
        items += f'''<a href="/blog/{slug}" class="blog-card">
            <h3>{title}</h3>
            <p class="blog-card-desc">{desc}</p>
            <span class="blog-card-date">{date_str}</span>
        </a>\n'''

    if not items:
        items = '<p style="text-align:center;color:#9CA3AF;padding:40px;">No articles yet. Check back soon!</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blog — Jago Grahak Jago</title>
    <meta name="description" content="Consumer rights guides, legal tips, and how-to articles for Indian consumers.">
    <link rel="canonical" href="{base}/blog">
    <meta property="og:title" content="Blog — Jago Grahak Jago">
    <meta property="og:description" content="Consumer rights guides, legal tips, and how-to articles.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/style.css">
    <style>
        .blog-hero {{ text-align: center; padding: 48px 24px; background: linear-gradient(170deg, #FFF8E1, #fff 60%); }}
        .blog-hero h1 {{ font-size: 2rem; color: #111827; margin-bottom: 8px; }}
        .blog-hero p {{ color: #6B7280; }}
        .blog-grid {{ max-width: 720px; margin: 0 auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }}
        .blog-card {{ display: block; background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,.1); text-decoration: none; color: inherit; transition: box-shadow .2s; }}
        .blog-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,.12); }}
        .blog-card h3 {{ font-size: 1.2rem; color: #111827; margin-bottom: 6px; }}
        .blog-card-desc {{ color: #6B7280; font-size: .9rem; margin-bottom: 6px; }}
        .blog-card-date {{ color: #9CA3AF; font-size: .8rem; }}
        .blog-nav {{ max-width: 720px; margin: 0 auto; padding: 16px 24px; }}
        .blog-nav a {{ color: #DC2626; text-decoration: none; font-weight: 600; }}
    </style>
</head>
<body>
    <nav class="blog-nav"><a href="/">\u2190 Back to Jago Grahak Jago</a></nav>
    <div class="blog-hero">
        <h1>Consumer Rights Blog</h1>
        <p>Guides, legal tips, and know-your-rights articles for Indian consumers</p>
    </div>
    <div class="blog-grid">{items}</div>
</body>
</html>"""


@app.get("/blog")
async def blog_index():
    posts = notice_store.get_published_blog_posts()
    seo = notice_store.get_seo_settings()
    return HTMLResponse(content=_render_blog_index(posts, seo))


@app.get("/blog/{slug}")
async def blog_post_page(slug: str):
    post = notice_store.get_blog_post(slug)
    if not post or post.get("status") != "published":
        raise HTTPException(status_code=404, detail="Blog post not found")
    seo = notice_store.get_seo_settings()
    return HTMLResponse(content=_render_blog_html(post, seo))


# ── Database API endpoints ───────────────────────────────────────────

@app.get("/api/admin/db/users")
async def list_users(limit: int = 100, offset: int = 0, _=Depends(require_admin)):
    """List all users stored in the database."""
    return await db.get_all_users(limit, offset)


@app.get("/api/admin/db/users/{user_id}")
async def get_user_detail(user_id: str, _=Depends(require_admin)):
    """Get a single user with all their notices."""
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["notices"] = await db.get_user_notices(user_id)
    return user


@app.get("/api/admin/db/notices")
async def list_db_notices(limit: int = 100, offset: int = 0, _=Depends(require_admin)):
    """List all notices with full interim analysis data from the database."""
    return await db.get_all_notices_db(limit, offset)


@app.get("/api/admin/db/notices/{notice_id}")
async def get_db_notice_detail(notice_id: str, _=Depends(require_admin)):
    """Get a single notice with all interim model outputs."""
    notice = await db.get_notice_db(notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return notice


@app.get("/api/admin/db/stats")
async def get_db_stats(_=Depends(require_admin)):
    """Get database-only dashboard stats (users, analyses, notices)."""
    return await db.get_dashboard_stats_db()


@app.get("/api/admin/db/pdfs")
async def list_pdfs(limit: int = 100, offset: int = 0, _=Depends(require_admin)):
    """List all stored generated PDFs (metadata only)."""
    return await db.get_all_pdfs_meta(limit, offset)


@app.get("/api/admin/db/pdfs/{notice_id}")
async def download_db_pdf(notice_id: str, _=Depends(require_admin)):
    """Download a stored PDF by notice ID."""
    result = await db.get_pdf(notice_id)
    if not result:
        raise HTTPException(status_code=404, detail="PDF not found for this notice")
    pdf_bytes, filename = result
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Email / Notification Management ─────────────────────────────────

class EmailSettingsUpdate(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    from_name: str | None = None
    from_email: str | None = None
    use_tls: bool | None = None
    admin_alert_email: str | None = None
    templates: dict | None = None
    auto_send_notice_ready: bool | None = None
    auto_send_admin_alert: bool | None = None
    follow_up_days: int | None = None


class SendTestEmailRequest(BaseModel):
    to_email: str
    template: str = "notice_ready"


@app.get("/api/admin/email/settings")
async def get_email_settings(_=Depends(require_admin)):
    settings = notice_store.get_email_settings()
    # Mask password for security
    if settings.get("smtp_password"):
        settings["smtp_password"] = "••••••••"
    return settings


@app.put("/api/admin/email/settings")
async def save_email_settings(body: EmailSettingsUpdate, _=Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    # Don't save masked password
    if data.get("smtp_password") == "••••••••":
        del data["smtp_password"]
    result = notice_store.save_email_settings(data)
    notice_store.log_activity("Updated email settings", "", "email")
    # Mask in response
    if result.get("smtp_password"):
        result["smtp_password"] = "••••••••"
    return result


@app.get("/api/admin/email/log")
async def get_email_log(limit: int = 100, _=Depends(require_admin)):
    return notice_store.get_email_log(limit)


@app.post("/api/admin/email/test")
async def send_test_email(body: SendTestEmailRequest, _=Depends(require_admin)):
    """Send a test email using current SMTP settings."""
    settings = notice_store.get_email_settings()
    if not settings.get("smtp_user") or not settings.get("from_email"):
        raise HTTPException(status_code=400, detail="SMTP not configured. Set host, user, password, from_email first.")
    try:
        from legaltech.services.email_service import send_notice_email
        # Use stored SMTP settings by setting env vars temporarily
        import os
        os.environ["SMTP_HOST"] = settings.get("smtp_host", "")
        os.environ["SMTP_PORT"] = str(settings.get("smtp_port", 587))
        os.environ["SMTP_USER"] = settings.get("smtp_user", "")
        os.environ["SMTP_PASSWORD"] = settings.get("smtp_password", "")
        os.environ["NOTICE_FROM_NAME"] = settings.get("from_name", "Lawly")
        os.environ["NOTICE_FROM_EMAIL"] = settings.get("from_email", "")
        os.environ["SMTP_USE_TLS"] = "true" if settings.get("use_tls", True) else "false"

        template = settings.get("templates", {}).get(body.template, {})
        subject = template.get("subject", f"Test Email — {body.template}").replace("{{name}}", "Test User").replace("{{company}}", "Test Co")
        body_text = template.get("body", "This is a test email from Lawly admin.").replace("{{name}}", "Test User").replace("{{company}}", "Test Co").replace("{{notice_id}}", "TEST123").replace("{{amount}}", "₹199").replace("{{tier}}", "self_send").replace("{{days}}", "15").replace("{{time}}", "now").replace("{{email}}", body.to_email).replace("{{notice_link}}", "https://lawly.store")

        result = send_notice_email(
            to_email=body.to_email,
            to_name="Test User",
            subject=subject,
            body_text=body_text,
            pdf_bytes=b"",
            pdf_filename="",
        )
        status = "sent" if result.success else "failed"
        notice_store.log_email({
            "to": body.to_email,
            "subject": subject,
            "template": f"test_{body.template}",
            "status": status,
            "error": "" if result.success else result.message,
        })
        if result.success:
            return {"ok": True, "message": f"Test email sent to {body.to_email}"}
        raise HTTPException(status_code=500, detail=result.message)
    except HTTPException:
        raise
    except Exception as e:
        notice_store.log_email({
            "to": body.to_email,
            "subject": "Test email",
            "template": f"test_{body.template}",
            "status": "failed",
            "error": str(e),
        })
        raise HTTPException(status_code=500, detail=f"Failed to send: {e}")


# ── Analytics ────────────────────────────────────────────────────────

class TrackEventRequest(BaseModel):
    event: str
    data: dict | None = None


@app.post("/api/track")
async def track_event(body: TrackEventRequest):
    """Public endpoint to track funnel events from the frontend."""
    allowed = {"page_view", "notice_started", "notice_generated", "pdf_downloaded", "payment"}
    if body.event not in allowed:
        raise HTTPException(status_code=400, detail="Invalid event type")
    return notice_store.track_event(body.event, body.data or {})


@app.get("/api/admin/analytics")
async def get_analytics(_=Depends(require_admin)):
    """Return analytics summary for the admin dashboard."""
    return notice_store.get_analytics_summary()


@app.get("/api/admin/analytics/events")
async def get_analytics_events(limit: int = 200, _=Depends(require_admin)):
    return notice_store.get_analytics_events(limit)


# ── Search Insights (Bing Webmaster) ────────────────────────────────

from legaltech.services import search_insights


@app.get("/api/admin/insights")
async def get_search_insights(_=Depends(require_admin)):
    """Aggregated Bing Webmaster search insights for the admin dashboard."""
    return await search_insights.get_insights_summary()


@app.get("/api/admin/insights/queries")
async def get_insights_queries(_=Depends(require_admin)):
    return await search_insights.get_query_stats()


@app.get("/api/admin/insights/crawl")
async def get_insights_crawl(_=Depends(require_admin)):
    return await search_insights.get_crawl_stats()


@app.get("/api/admin/insights/pages")
async def get_insights_pages(_=Depends(require_admin)):
    return await search_insights.get_page_stats()


class SubmitUrlRequest(BaseModel):
    url: str


class SubmitUrlBatchRequest(BaseModel):
    urls: list[str]


@app.post("/api/admin/insights/submit-url")
async def insights_submit_url(body: SubmitUrlRequest, _=Depends(require_admin)):
    """Submit a URL to Bing for indexing."""
    result = await search_insights.submit_url(body.url)
    if result.get("ok"):
        notice_store.log_activity("Bing URL submitted", body.url)
    return result


@app.post("/api/admin/insights/submit-batch")
async def insights_submit_batch(body: SubmitUrlBatchRequest, _=Depends(require_admin)):
    """Submit multiple URLs to Bing for indexing."""
    result = await search_insights.submit_url_batch(body.urls)
    if result.get("ok"):
        notice_store.log_activity("Bing batch submitted", f"{len(body.urls)} URLs")
    return result


# ── Support / Contact Tickets ────────────────────────────────────────

class CreateTicketRequest(BaseModel):
    name: str
    email: str
    subject: str
    message: str
    category: str = "general"
    notice_id: str = ""


class UpdateTicketRequest(BaseModel):
    status: str | None = None
    priority: str | None = None
    admin_notes: str | None = None


class TicketReplyRequest(BaseModel):
    message: str
    from_who: str = "admin"


@app.post("/api/contact")
async def create_support_ticket(body: CreateTicketRequest):
    """Public endpoint — anyone can submit a support ticket."""
    ticket = notice_store.create_ticket(body.model_dump())
    notice_store.log_activity("New support ticket", f"{body.subject} from {body.email}", "ticket", ticket["id"])
    # Send admin alert email if configured
    email_settings = notice_store.get_email_settings()
    if email_settings.get("admin_alert_email") and email_settings.get("smtp_user"):
        try:
            from legaltech.services.email_service import send_notice_email
            import os
            os.environ["SMTP_HOST"] = email_settings.get("smtp_host", "")
            os.environ["SMTP_PORT"] = str(email_settings.get("smtp_port", 587))
            os.environ["SMTP_USER"] = email_settings.get("smtp_user", "")
            os.environ["SMTP_PASSWORD"] = email_settings.get("smtp_password", "")
            os.environ["NOTICE_FROM_NAME"] = email_settings.get("from_name", "Lawly")
            os.environ["NOTICE_FROM_EMAIL"] = email_settings.get("from_email", "")
            send_notice_email(
                to_email=email_settings["admin_alert_email"],
                to_name="Admin",
                subject=f"[Lawly Support] {body.subject}",
                body_text=f"New support ticket from {body.name} ({body.email}):\n\nCategory: {body.category}\n\n{body.message}",
                pdf_bytes=b"",
                pdf_filename="",
            )
        except Exception:
            logger.warning("Admin alert email failed", exc_info=True)
    return {"ok": True, "ticket_id": ticket["id"], "message": "Ticket submitted successfully"}


@app.get("/api/admin/tickets")
async def list_tickets(_=Depends(require_admin)):
    return notice_store.get_all_tickets()


@app.get("/api/admin/tickets/stats")
async def ticket_stats(_=Depends(require_admin)):
    return notice_store.get_ticket_stats()


@app.get("/api/admin/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, _=Depends(require_admin)):
    ticket = notice_store.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.put("/api/admin/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, body: UpdateTicketRequest, _=Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    ticket = notice_store.update_ticket(ticket_id, data)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    notice_store.log_activity("Updated ticket", f"#{ticket_id} → {data.get('status', '')}", "ticket", ticket_id)
    return ticket


@app.post("/api/admin/tickets/{ticket_id}/reply")
async def reply_to_ticket(ticket_id: str, body: TicketReplyRequest, _=Depends(require_admin)):
    ticket = notice_store.add_ticket_reply(ticket_id, {"from": body.from_who, "message": body.message})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    notice_store.log_activity("Replied to ticket", f"#{ticket_id}", "ticket", ticket_id)
    return ticket


# ── Version management ───────────────────────────────────────────────

ALLOWED_BUCKETS = {"lawly.store", os.getenv("DATA_BUCKET", "lawly-data-prod")}


@app.get("/api/admin/versions")
async def list_versions(bucket: str | None = None, _=Depends(require_admin)):
    b = bucket or "lawly-data-prod"
    if b not in ALLOWED_BUCKETS:
        raise HTTPException(status_code=400, detail="Invalid bucket")
    return notice_store.list_versioned_files(b)


@app.get("/api/admin/versions/file")
async def list_file_versions(key: str, bucket: str | None = None, _=Depends(require_admin)):
    b = bucket or "lawly-data-prod"
    if b not in ALLOWED_BUCKETS:
        raise HTTPException(status_code=400, detail="Invalid bucket")
    return notice_store.list_file_versions(key, b)


@app.get("/api/admin/versions/content")
async def get_version_content(key: str, version_id: str, bucket: str | None = None, _=Depends(require_admin)):
    b = bucket or "lawly-data-prod"
    if b not in ALLOWED_BUCKETS:
        raise HTTPException(status_code=400, detail="Invalid bucket")
    try:
        content, content_type = notice_store.get_file_version_content(key, version_id, b)
    except Exception:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"content": content, "content_type": content_type}


class RevertRequest(BaseModel):
    key: str
    version_id: str
    bucket: str | None = None


@app.post("/api/admin/versions/revert")
async def revert_version(body: RevertRequest, _=Depends(require_admin)):
    b = body.bucket or "lawly-data-prod"
    if b not in ALLOWED_BUCKETS:
        raise HTTPException(status_code=400, detail="Invalid bucket")
    result = notice_store.revert_file_version(body.key, body.version_id, b)
    notice_store.log_activity("Reverted file", f"{body.key} → version {body.version_id[:8]}…", "version")
    return result


# ── AI Tools for Admin ───────────────────────────────────────────────

class AIGenerateRequest(BaseModel):
    tool: str          # e.g. "blog_post", "seo_meta", "email_template", "ticket_reply", etc.
    context: dict = {} # tool-specific input data


@app.post("/api/admin/ai/generate")
async def ai_generate(body: AIGenerateRequest, _=Depends(require_admin)):
    """AI-powered content generation for admin tools."""
    llm = pipeline.llm_fast  # Use Haiku for speed + lower cost

    tool = body.tool
    ctx = body.context

    try:
        if tool == "blog_post":
            topic = ctx.get("topic", "").strip()
            keywords = ctx.get("keywords", "").strip()
            tone = ctx.get("tone", "professional, informative")
            if not topic:
                raise HTTPException(status_code=400, detail="topic is required")
            result = await llm.complete_json(
                system_prompt=(
                    "You are an expert legal content writer for an Indian consumer protection platform called Lawly (lawly.store). "
                    "Write blog posts that are SEO-optimized, informative, and helpful for Indian consumers. "
                    "Return JSON with keys: title, slug, meta_description (max 155 chars), meta_keywords (comma-separated), "
                    "content (full HTML blog post body with <h2>, <h3>, <p>, <ul>, <strong> tags — no <html>/<body>/<head> wrappers). "
                    "Content should be 800-1200 words, well-structured with subheadings, practical advice, and references to Indian law."
                ),
                user_prompt=f"Topic: {topic}\nTarget keywords: {keywords}\nTone: {tone}",
                max_tokens=4096,
            )
            return {"ok": True, "result": result}

        elif tool == "blog_improve":
            content = ctx.get("content", "").strip()
            title = ctx.get("title", "").strip()
            instruction = ctx.get("instruction", "Improve readability, SEO, and add more detail")
            if not content:
                raise HTTPException(status_code=400, detail="content is required")
            result = await llm.complete_json(
                system_prompt=(
                    "You are an expert editor for a legal consumer protection blog. "
                    "Improve the given blog post content based on the instruction. "
                    "Return JSON with keys: content (improved HTML), meta_description (max 155 chars), "
                    "meta_keywords (comma-separated), suggestions (array of strings — brief improvement notes)."
                ),
                user_prompt=f"Title: {title}\nInstruction: {instruction}\nCurrent content:\n{content[:6000]}",
                max_tokens=4096,
            )
            return {"ok": True, "result": result}

        elif tool == "seo_meta":
            page_title = ctx.get("title", "").strip()
            page_content = ctx.get("content", "").strip()
            page_url = ctx.get("url", "").strip()
            if not page_title and not page_content:
                raise HTTPException(status_code=400, detail="title or content is required")
            result = await llm.complete_json(
                system_prompt=(
                    "You are an SEO specialist for Lawly, an Indian consumer legal notice platform. "
                    "Generate optimized meta tags for the given page. "
                    "Return JSON with keys: site_title (50-60 chars), meta_description (120-155 chars), "
                    "meta_keywords (comma-separated, 5-8 keywords), og_title (under 60 chars), og_description (under 155 chars). "
                    "Focus on Indian consumer protection search intent."
                ),
                user_prompt=f"Page title: {page_title}\nURL: {page_url}\nContent excerpt: {page_content[:2000]}",
                max_tokens=1024,
            )
            return {"ok": True, "result": result}

        elif tool == "seo_faq":
            topic = ctx.get("topic", "Indian consumer legal notice").strip()
            existing_faqs = ctx.get("existing_faqs", [])
            result = await llm.complete_json(
                system_prompt=(
                    "You are an SEO expert. Generate FAQ schema items for an Indian consumer protection legal notice platform. "
                    "Return JSON with key: faqs (array of objects with 'question' and 'answer' keys). "
                    "Generate 5 high-value FAQ items that target common search queries. "
                    "Answers should be concise (2-3 sentences), authoritative, and cite Indian laws where relevant."
                ),
                user_prompt=f"Topic: {topic}\nExisting FAQs to avoid duplicating: {existing_faqs[:5]}",
                max_tokens=2048,
            )
            return {"ok": True, "result": result}

        elif tool == "aeo_snippets":
            topic = ctx.get("topic", "").strip()
            existing = ctx.get("existing_snippets", [])
            result = await llm.complete_json(
                system_prompt=(
                    "You are an AI Engine Optimization (AEO) expert for Lawly, an Indian consumer protection platform. "
                    "Generate AI-ready answer snippets that AI assistants (ChatGPT, Google SGE, Perplexity) would surface. "
                    "Return JSON with key: snippets (array of objects with 'query' (the question users ask), "
                    "'answer' (concise 2-4 sentence authoritative answer), 'category' (topic area)). "
                    "Generate 4 snippets targeting high-intent consumer protection queries."
                ),
                user_prompt=f"Focus area: {topic or 'Indian consumer rights and legal notices'}\nExisting snippets to avoid: {[s.get('query','') for s in existing[:5]]}",
                max_tokens=2048,
            )
            return {"ok": True, "result": result}

        elif tool == "aeo_llms_txt":
            seo = notice_store.get_seo_settings()
            aeo = notice_store.get_aeo_settings()
            posts = notice_store.get_published_blog_posts()
            result = await llm.complete_text(
                system_prompt=(
                    "Generate a comprehensive llms.txt file for an AI-powered Indian consumer legal notice platform called Lawly (lawly.store). "
                    "This file helps AI crawlers understand the site. Follow the llms.txt standard format:\n"
                    "- Start with # Site Name\n- > One-line description\n- ## Sections with content\n"
                    "Include: About, Key Features, Services, Pricing, Legal Framework, How It Works, FAQ, Contact Info."
                ),
                user_prompt=f"Site title: {seo.get('site_title','')}\nDescription: {seo.get('meta_description','')}\n"
                           f"Blog posts: {[p.get('title','') for p in posts[:10]]}\n"
                           f"Existing org info: {aeo.get('org_schema',{})}",
                max_tokens=2048,
            )
            return {"ok": True, "result": {"llms_txt": result.strip()}}

        elif tool == "aeo_topic_clusters":
            existing = ctx.get("existing_clusters", [])
            result = await llm.complete_json(
                system_prompt=(
                    "You are a content strategist for Lawly, an Indian consumer protection platform. "
                    "Generate topic authority clusters that demonstrate expertise. "
                    "Return JSON with key: clusters (array of objects with 'name' (cluster topic), "
                    "'pillar' (main pillar content idea), 'subtopics' (array of 4-6 related subtopic strings)). "
                    "Generate 3 clusters focused on Indian consumer law."
                ),
                user_prompt=f"Existing clusters: {[c.get('name','') for c in existing[:5]]}",
                max_tokens=2048,
            )
            return {"ok": True, "result": result}

        elif tool == "email_template":
            template_type = ctx.get("type", "notice_ready").strip()
            custom_instruction = ctx.get("instruction", "").strip()
            result = await llm.complete_json(
                system_prompt=(
                    "You are an email copywriting expert for Lawly, an Indian consumer legal notice platform. "
                    "Generate a professional transactional email template. "
                    "Use these placeholders: {{name}}, {{company}}, {{notice_id}}, {{amount}}, {{tier}}, {{days}}, {{time}}, {{email}}, {{notice_link}}. "
                    "Return JSON with keys: subject (email subject line), body (plain text email body). "
                    "Keep it professional, empathetic, and action-oriented."
                ),
                user_prompt=f"Template type: {template_type}\nAdditional instructions: {custom_instruction}",
                max_tokens=1024,
            )
            return {"ok": True, "result": result}

        elif tool == "ticket_reply":
            ticket = ctx.get("ticket", {})
            instruction = ctx.get("instruction", "Draft a helpful, empathetic reply")
            result = await llm.complete_json(
                system_prompt=(
                    "You are a customer support specialist for Lawly, an Indian consumer legal notice platform. "
                    "Draft a professional, empathetic support reply. "
                    "Return JSON with keys: reply (the reply text), suggested_status (one of: open, in_progress, resolved, closed). "
                    "Be helpful, reference Indian consumer protection rights where relevant, and suggest next steps."
                ),
                user_prompt=f"Ticket subject: {ticket.get('subject','')}\n"
                           f"Customer message: {ticket.get('message','')}\n"
                           f"Category: {ticket.get('category','')}\n"
                           f"Current status: {ticket.get('status','open')}\n"
                           f"Previous replies: {ticket.get('replies', [])[-3:]}\n"
                           f"Instruction: {instruction}",
                max_tokens=1024,
            )
            return {"ok": True, "result": result}

        elif tool == "notice_review":
            notice_text = ctx.get("notice_text", "").strip()
            if not notice_text:
                raise HTTPException(status_code=400, detail="notice_text is required")
            result = await llm.complete_json(
                system_prompt=(
                    "You are a senior Indian consumer law expert reviewing a legal notice. "
                    "Analyze the notice for legal accuracy, completeness, and effectiveness. "
                    "Return JSON with keys: score (0-100), grade (A/B/C/D/F), "
                    "strengths (array of strings), weaknesses (array of strings), "
                    "suggestions (array of strings), reviewer_notes (summary paragraph for admin)."
                ),
                user_prompt=f"Legal notice to review:\n{notice_text[:8000]}",
                max_tokens=2048,
            )
            return {"ok": True, "result": result}

        elif tool == "page_meta":
            path = ctx.get("path", "").strip()
            title = ctx.get("title", "").strip()
            result = await llm.complete_json(
                system_prompt=(
                    "You are an SEO specialist for Lawly, an Indian consumer legal notice platform. "
                    "Generate optimized page metadata. "
                    "Return JSON with keys: title, meta_description (120-155 chars), meta_keywords (comma-separated), "
                    "og_title, og_description."
                ),
                user_prompt=f"Page path: {path}\nPage title hint: {title}\nSite: Lawly — AI-powered consumer legal notices for India",
                max_tokens=512,
            )
            return {"ok": True, "result": result}

        elif tool == "keyword_ideas":
            seed = ctx.get("seed_keyword", "consumer legal notice India").strip()
            result = await llm.complete_json(
                system_prompt=(
                    "You are an SEO keyword researcher for Indian consumer protection topics. "
                    "Generate keyword ideas with search intent classification. "
                    "Return JSON with key: keywords (array of objects with 'keyword', 'intent' (informational/transactional/navigational), "
                    "'difficulty' (low/medium/high), 'suggestion' (how to target it))). "
                    "Generate 10 keywords."
                ),
                user_prompt=f"Seed keyword: {seed}",
                max_tokens=2048,
            )
            return {"ok": True, "result": result}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown AI tool: {tool}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("AI generation failed for tool=%s", tool)
        raise HTTPException(status_code=500, detail=f"AI generation failed: {e}")


# ── 301 Redirect handler (catch-all, must be last) ──────────────────

@app.get("/{full_path:path}")
async def catch_all_redirect(full_path: str):
    """Serve static files or follow 301 redirects."""
    path = f"/{full_path}" if not full_path.startswith("/") else full_path
    # Check redirects
    redir = notice_store.find_redirect(path)
    if redir:
        from fastapi.responses import RedirectResponse
        code = redir.get("status_code", 301)
        return RedirectResponse(url=redir["to_path"], status_code=code)
    # Try static file
    static_path = _STATIC_DIR / full_path
    if static_path.is_file():
        return FileResponse(str(static_path))
    raise HTTPException(status_code=404, detail="Not found")
