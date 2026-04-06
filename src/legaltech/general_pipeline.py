"""GeneralDocumentPipeline — lightweight pipeline for any-document generation.

Unlike the specialist LegalNoticePipeline (which orchestrates 10+ agents and does
web research), this pipeline is intentionally minimal:

  1. Document agent drafts the full text.
  2. Metadata (statutes cited, filing notes) is extracted from the draft.
  3. The result is returned as a `GeneratedDocument`.

No web scraping, no company lookup, no database writes — those remain the
responsibility of the caller (e.g. the FastAPI route, which may persist to DB).
"""
from __future__ import annotations

import logging
from datetime import datetime

from legaltech.agents.document_agent import GeneralDocumentAgent
from legaltech.config.settings import get_settings
from legaltech.schemas import DocumentType, GeneratedDocument, LegalDocumentRequest, get_document_type_config
from legaltech.services.llm import LLMService

logger = logging.getLogger(__name__)


class GeneralDocumentPipeline:
    """Generates any supported legal document from a `LegalDocumentRequest`."""

    def __init__(self) -> None:
        settings = get_settings()
        # Full / heavy model for document drafting (quality matters more here)
        self._llm = LLMService(
            model_name=settings.model_name,
            api_key=settings.anthropic_api_key,
        )
        self._agent = GeneralDocumentAgent(llm=self._llm)

    async def generate(self, req: LegalDocumentRequest) -> GeneratedDocument:
        """Run the full document generation flow and return a `GeneratedDocument`."""
        logger.info(
            "GeneralDocumentPipeline.generate: type=%s sender=%s",
            req.document_type.value, req.sender_name,
        )
        draft = await self._agent.draft(req)
        return GeneratedDocument(
            document_type=req.document_type,
            title=draft.title,
            body=draft.body,
            applicable_law=draft.applicable_law,
            filing_notes=draft.filing_notes,
            generated_at=datetime.utcnow(),
        )

    @staticmethod
    def get_document_type_metadata(document_type: str | DocumentType) -> dict:
        """Return full UI metadata for a single document type."""
        doc_key = document_type.value if isinstance(document_type, DocumentType) else str(document_type)
        config = dict(get_document_type_config(doc_key))
        config["id"] = doc_key
        config.setdefault("label", doc_key.replace("_", " ").title())
        config.setdefault("description", "")
        config.setdefault("needs_recipient", True)
        return config

    @staticmethod
    def list_document_types() -> list[dict]:
        """Return UI-friendly metadata for all supported document types."""
        return [
            GeneralDocumentPipeline.get_document_type_metadata(dt)
            for dt in DocumentType
        ]
