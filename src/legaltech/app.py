from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from legaltech.pipeline import LegalNoticePipeline
from legaltech.schemas import Complainant, ComplaintInput, IntakeMode, ServiceTier
from legaltech.services.pdf_generator import generate_pdf
from legaltech.services import store as notice_store

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"

app = FastAPI(title="Indian Legal Notice Agent", version="0.4.0")
pipeline = LegalNoticePipeline()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://playtym.github.io",
        "https://v5pah3m82k.ap-south-1.awsapprunner.com",
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
    follow_up_answers: dict[str, str] | None = None  # answers to questions from /analyze


class AnalyzeRequest(BaseModel):
    """Request body for /notice/analyze — same complaint fields, plus optional previous answers."""
    complainant: Complainant
    issue_summary: str
    desired_resolution: str
    company_name_hint: str | None = None
    website: HttpUrl | None = None
    timeline: list[str] = []
    evidence: list[str] = []
    jurisdiction: str = "India"
    previous_answers: dict[str, str] | None = None  # answers from a prior /analyze round


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
        packet = await pipeline.run(
            complaint,
            tier=payload.tier,
            follow_up_answers=payload.follow_up_answers,
        )
        result = packet.model_dump()
        company_label = packet.company.legal_name or packet.company.brand_name or payload.company_name_hint or "Unknown"
        notice_id = notice_store.save_notice(
            complainant_name=payload.complainant.full_name,
            complainant_email=payload.complainant.email,
            company_name=company_label,
            tier=payload.tier.value if hasattr(payload.tier, "value") else str(payload.tier),
            legal_notice=packet.legal_notice,
        )
        result["notice_id"] = notice_id
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc


@app.post("/notice/analyze")
async def analyze_case(payload: AnalyzeRequest):
    """Phase 1: Analyze the complaint and return follow-up questions.

    Call this BEFORE /notice/typed. If ready_to_generate is False,
    present the questions to the user, collect answers, and call
    /notice/analyze again with previous_answers until ready.
    """
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
        result = await pipeline.analyze(
            complaint,
            previous_answers=payload.previous_answers,
        )
        return result.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


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
        )
        return packet.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc


@app.post("/translate/to-english")
async def translate_to_english(payload: TranslateRequest):
    source = payload.text.strip()
    if not source:
        return {"translated_text": ""}

    try:
        translated = await pipeline.llm.complete_text(
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
        raise HTTPException(status_code=500, detail=f"Translation failed: {exc}") from exc


@app.post("/intake/from-transcript")
async def intake_from_transcript(payload: TranscriptIntakeRequest):
    source = payload.transcript_text.strip()
    if not source:
        raise HTTPException(status_code=400, detail="Transcript is empty")

    try:
        extraction = await pipeline.llm.complete_json(
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
            answer_obj = await pipeline.llm.complete_json(
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
        raise HTTPException(status_code=500, detail=f"Transcript intake failed: {exc}") from exc


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
        refined = await pipeline.llm.complete_json(
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
        packet = await pipeline.run(
            complaint,
            tier=payload.tier,
            follow_up_answers=payload.follow_up_answers,
        )
        is_lawyer = payload.tier == ServiceTier.lawyer_assisted
        pdf_bytes = generate_pdf(packet.legal_notice, is_lawyer_tier=is_lawyer)
        company_label = packet.company.legal_name or packet.company.brand_name or "Company"
        filename = f"Legal_Notice_{company_label.replace(' ', '_')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc


# ── Root redirect ────────────────────────────────────────────────────

@app.get("/")
async def root():
    return FileResponse(str(_STATIC_DIR / "index.html"))


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


@app.get("/api/admin/lawyer")
async def get_lawyer():
    data = notice_store.get_lawyer()
    return data or {}


@app.put("/api/admin/lawyer")
async def save_lawyer(details: LawyerDetails):
    return notice_store.save_lawyer(details.model_dump())


@app.get("/api/admin/notices")
async def get_notices():
    return notice_store.get_all_notices()


@app.get("/api/admin/notices/{notice_id}")
async def get_notice_detail(notice_id: str):
    notice = notice_store.get_notice(notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return notice


@app.put("/api/admin/notices/{notice_id}/status")
async def update_notice_status(notice_id: str, body: NoticeStatusUpdate):
    result = notice_store.update_notice_status(notice_id, body.status, body.reviewer_notes)
    if not result:
        raise HTTPException(status_code=404, detail="Notice not found")
    return result


@app.get("/api/admin/notices/{notice_id}/pdf")
async def get_notice_pdf(notice_id: str):
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
