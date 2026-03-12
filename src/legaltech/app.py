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
        "https://xgp73pem2c.ap-south-1.awsapprunner.com",
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
