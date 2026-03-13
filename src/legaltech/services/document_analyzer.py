"""Intelligent document analysis using Claude.

Analyzes uploaded evidence documents (images, PDFs) to extract
key facts, dates, amounts, and assess relevance to the consumer dispute.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _extract_text_from_pdf(data: bytes) -> str:
    """Extract text from a PDF using basic binary parsing.

    Falls back to empty string if extraction fails.
    """
    # Simple stream-based text extraction for common PDFs
    text_chunks: list[str] = []
    try:
        import re
        # Extract text between BT and ET operators (basic PDF text extraction)
        content = data.decode("latin-1", errors="ignore")
        # Find text within parentheses in PDF streams
        for match in re.finditer(r"\(([^)]{1,500})\)", content):
            chunk = match.group(1).strip()
            if len(chunk) > 2 and any(c.isalpha() for c in chunk):
                text_chunks.append(chunk)
    except Exception:
        pass

    return " ".join(text_chunks[:200])  # Cap at reasonable length


async def analyze_documents(
    llm: Any,
    files: list,
) -> dict[str, Any]:
    """Analyze uploaded documents using Claude to extract relevant information.

    Args:
        llm: LLMService instance for Claude calls.
        files: List of StoredFile objects from upload_store.

    Returns:
        Dict with 'documents' key containing analysis for each file.
    """
    results: list[dict[str, Any]] = []

    for sf in files:
        try:
            if sf.is_image():
                analysis = await _analyze_image(llm, sf)
            elif sf.content_type == "application/pdf":
                analysis = await _analyze_pdf(llm, sf)
            else:
                analysis = {
                    "filename": sf.filename,
                    "document_type": "unknown",
                    "relevance": "low",
                    "summary": f"Unsupported file type: {sf.content_type}",
                    "key_facts": [],
                    "amounts": [],
                    "dates": [],
                }
            results.append(analysis)
        except Exception as exc:
            logger.warning("Document analysis failed for %s: %s", sf.filename, exc)
            results.append({
                "filename": sf.filename,
                "document_type": "unknown",
                "relevance": "unknown",
                "summary": f"Analysis failed: {exc}",
                "key_facts": [],
                "amounts": [],
                "dates": [],
            })

    return {"documents": results}


_DOC_ANALYSIS_SYSTEM = """\
You are an expert legal document analyst for Indian consumer disputes. \
Analyze the provided document and extract ALL legally relevant information.

Return strict JSON with these keys:
{
  "document_type": "invoice|receipt|screenshot|chat_log|email|contract|bank_statement|complaint_ticket|id_proof|other",
  "relevance": "high|medium|low",
  "summary": "2-3 sentence summary of what this document shows",
  "key_facts": ["fact 1", "fact 2", ...],
  "amounts": ["₹78,999 (product price)", "₹25,000 (claimed refund)", ...],
  "dates": ["05 Feb 2025 (order date)", "12 Feb 2025 (complaint date)", ...],
  "parties": ["Amazon India", "Priya Sharma", ...],
  "reference_numbers": ["Order #404-1234567", "Ticket #INC0012345", ...],
  "legal_relevance": "How this document supports the consumer's case"
}

Be thorough — extract EVERY date, amount, name, reference number, and fact. \
These will be used in a formal legal notice.
Return ONLY valid JSON.
"""


async def _analyze_image(llm: Any, sf: Any) -> dict[str, Any]:
    """Analyze an image document using Claude's vision capability."""
    b64_data = base64.b64encode(sf.data).decode("ascii")
    media_type = sf.content_type

    # Use the Anthropic messages API with image content
    message = await llm.client.messages.create(
        model=llm.model_name,
        max_tokens=2000,
        system=_DOC_ANALYSIS_SYSTEM,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64_data,
                    },
                },
                {
                    "type": "text",
                    "text": f"Analyze this document image (filename: {sf.filename}). Extract all legally relevant information for a consumer dispute case.",
                },
            ],
        }],
    )

    return _parse_analysis_response(message.content[0].text, sf.filename)


async def _analyze_pdf(llm: Any, sf: Any) -> dict[str, Any]:
    """Analyze a PDF document by extracting text and sending to Claude."""
    extracted_text = _extract_text_from_pdf(sf.data)

    if not extracted_text.strip():
        # If text extraction failed, try as binary description
        extracted_text = f"[PDF file: {sf.filename}, size: {len(sf.data):,} bytes. Text extraction yielded no readable content.]"

    prompt = (
        f"Analyze this document (filename: {sf.filename}).\n\n"
        f"Extracted text content:\n{extracted_text[:8000]}\n\n"
        "Extract all legally relevant information for a consumer dispute case."
    )

    text = await llm.complete_text(_DOC_ANALYSIS_SYSTEM, prompt, max_tokens=2000)
    return _parse_analysis_response(text, sf.filename)


def _parse_analysis_response(text: str, filename: str) -> dict[str, Any]:
    """Parse Claude's JSON response into a structured analysis dict."""
    import json

    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_nl = cleaned.index("\n")
        last_fence = cleaned.rfind("```")
        cleaned = cleaned[first_nl + 1:last_fence].strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "filename": filename,
            "document_type": "unknown",
            "relevance": "medium",
            "summary": cleaned[:500],
            "key_facts": [],
            "amounts": [],
            "dates": [],
        }

    result["filename"] = filename
    # Ensure all expected keys exist
    for key in ("document_type", "relevance", "summary", "key_facts", "amounts", "dates"):
        if key not in result:
            result[key] = [] if key in ("key_facts", "amounts", "dates") else "unknown"

    return result
