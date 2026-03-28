lfrom fastapi import APIRouter
from src.legaltech.app import *

router = APIRouter(tags=['chat'])

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


@router.post("/translate/to-english")
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


@router.post("/intake/from-transcript")
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


@router.post("/speech/refine")
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
