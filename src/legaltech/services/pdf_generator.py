"""PDF legal notice generator.

Produces a professionally formatted PDF letter suitable for serving
as a legal notice. Uses reportlab for zero-system-dependency PDF
generation (no wkhtmltopdf or WeasyPrint headless browser needed).
"""

from __future__ import annotations

import io
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image as RLImage,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.colors import HexColor


_PAGE_W, _PAGE_H = A4
_MARGIN = 2.2 * cm


def _build_styles() -> dict[str, ParagraphStyle]:
    """Create a professional legal notice stylesheet."""
    base = getSampleStyleSheet()
    dark = HexColor("#111111")

    return {
        "title": ParagraphStyle(
            "NoticeTitle",
            parent=base["Heading1"],
            fontSize=18,
            leading=24,
            alignment=TA_CENTER,
            textColor=dark,
            spaceBefore=2 * mm,
            spaceAfter=2 * mm,
            fontName="Times-Bold",
        ),
        "section": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontSize=11,
            leading=15,
            textColor=dark,
            spaceBefore=6 * mm,
            spaceAfter=2 * mm,
            fontName="Times-Bold",
        ),
        "heading": ParagraphStyle(
            "Heading",
            parent=base["Heading2"],
            fontSize=11,
            leading=15,
            textColor=dark,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
            fontName="Times-Bold",
        ),
        "body": ParagraphStyle(
            "BodyText",
            parent=base["Normal"],
            fontSize=10.5,
            leading=15,
            alignment=TA_JUSTIFY,
            textColor=dark,
            spaceAfter=3 * mm,
            fontName="Times-Roman",
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            parent=base["Normal"],
            fontSize=10.5,
            leading=15,
            alignment=TA_JUSTIFY,
            textColor=dark,
            spaceAfter=3 * mm,
            fontName="Times-Bold",
        ),
        "meta": ParagraphStyle(
            "MetaInfo",
            parent=base["Normal"],
            fontSize=10,
            leading=13,
            textColor=dark,
            spaceAfter=1 * mm,
            fontName="Times-Roman",
        ),
        "subject": ParagraphStyle(
            "Subject",
            parent=base["Normal"],
            fontSize=10.5,
            leading=15,
            textColor=dark,
            spaceAfter=3 * mm,
            fontName="Times-Bold",
        ),
        "list_item": ParagraphStyle(
            "ListItem",
            parent=base["Normal"],
            fontSize=10.5,
            leading=15,
            alignment=TA_JUSTIFY,
            textColor=dark,
            spaceAfter=2 * mm,
            fontName="Times-Roman",
            leftIndent=8 * mm,
        ),
        "address": ParagraphStyle(
            "Address",
            parent=base["Normal"],
            fontSize=10.5,
            leading=14,
            textColor=dark,
            fontName="Times-Roman",
        ),
        "legal_quote": ParagraphStyle(
            "LegalQuote",
            parent=base["Normal"],
            fontSize=9.5,
            leading=13,
            alignment=TA_LEFT,
            textColor=HexColor("#222222"),
            leftIndent=12 * mm,
            rightIndent=8 * mm,
            spaceAfter=2 * mm,
            fontName="Times-Italic",
        ),
        "small": ParagraphStyle(
            "SmallText",
            parent=base["Normal"],
            fontSize=8,
            leading=10,
            textColor=HexColor("#666666"),
            fontName="Times-Roman",
        ),
        "warning": ParagraphStyle(
            "Warning",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=HexColor("#8b0000"),
            fontName="Times-Bold",
            spaceAfter=2 * mm,
        ),
    }


def _footer(canvas, doc):
    """Draw page number and confidential footer."""
    canvas.saveState()
    canvas.setFont("Times-Roman", 7)
    canvas.setFillColor(HexColor("#999999"))
    canvas.drawCentredString(
        _PAGE_W / 2, 1.2 * cm,
        f"Page {doc.page}"
    )
    canvas.restoreState()


def _esc(text: str) -> str:
    """Escape XML special characters for reportlab Paragraph."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ── Section headers recognised as formal headings in the PDF ──────────
_SECTION_HEADERS = {
    "STATEMENT OF FACTS", "LEGAL POSITION", "DEMAND AND RELIEF SOUGHT",
    "CONSEQUENCE OF NON-COMPLIANCE", "DEMANDS", "RELIEF SOUGHT",
    "LEGAL GROUNDS", "LEGAL ANALYSIS", "FACTS OF THE CASE",
    "CONSEQUENCES", "DEMAND", "FACTUAL BACKGROUND",
    "LEGAL SUBMISSIONS", "PRAYER", "RELIEFS CLAIMED",
}


def _strip_md(text: str) -> str:
    """Remove markdown bold markers."""
    return text.replace("**", "").strip()


def _md_to_rl(text: str) -> str:
    """Convert **bold** markdown to reportlab <b> tags; XML-escape the rest."""
    parts = re.split(r"(\*\*.*?\*\*)", text)
    out: list[str] = []
    for p in parts:
        if p.startswith("**") and p.endswith("**"):
            out.append(f"<b>{_esc(p[2:-2])}</b>")
        else:
            out.append(_esc(p))
    return "".join(out)


def generate_pdf(
    notice_text: str,
    *,
    is_lawyer_tier: bool = False,
    annexures: list[tuple[str, str, bytes]] | None = None,
) -> bytes:
    """Convert the structured notice text into a professional PDF letter.

    Args:
        notice_text: The full notice text (newline-delimited sections).
        is_lawyer_tier: If True, adds lawyer attestation footer.
        annexures: Optional list of (filename, content_type, data) tuples
                   to append as annexure pages.

    Returns:
        PDF file content as bytes.
    """
    if not notice_text or not notice_text.strip():
        logger.warning("Empty notice_text provided to generate_pdf. Generating placeholder PDF.")
        notice_text = "Notice text was empty or not provided."

    buf = io.BytesIO()
    styles = _build_styles()

    frame = Frame(
        _MARGIN, _MARGIN,
        _PAGE_W - 2 * _MARGIN,
        _PAGE_H - 2 * _MARGIN,
        id="main",
    )
    template = PageTemplate(id="letter", frames=[frame], onPage=_footer)
    doc = BaseDocTemplate(buf, pagesize=A4, pageTemplates=[template])

    _dark = HexColor("#111111")

    story: list = []
    lines = notice_text.split("\n")
    i = 0

    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()
        stripped = _strip_md(line)  # version without ** for pattern matching

        # Skip empty lines
        if not line:
            story.append(Spacer(1, 2 * mm))
            i += 1
            continue

        # ── Title: LEGAL NOTICE ──
        if stripped.upper() in ("LEGAL NOTICE", "NOTICE"):
            story.append(HRFlowable(
                width="100%", thickness=1.5, color=_dark,
                spaceBefore=2 * mm, spaceAfter=2 * mm,
            ))
            story.append(Paragraph(_esc(stripped.upper()), styles["title"]))
            story.append(HRFlowable(
                width="100%", thickness=1.5, color=_dark,
                spaceBefore=2 * mm, spaceAfter=6 * mm,
            ))
            i += 1
            continue

        # ── Date / Reference No metadata ──
        if stripped.startswith("Date:") or stripped.startswith("Reference No") or stripped.startswith("Ref:") or stripped.startswith("Ref."):
            story.append(Paragraph(_md_to_rl(line), styles["meta"]))
            i += 1
            continue

        # ── To / From address blocks ──
        if stripped in ("To,", "From,"):
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph(f"<b>{_esc(stripped)}</b>", styles["address"]))
            i += 1
            # Collect address lines until blank
            while i < len(lines) and lines[i].strip():
                addr_stripped = _strip_md(lines[i].strip())
                story.append(Paragraph(_esc(addr_stripped), styles["address"]))
                i += 1
            continue

        # ── Subject line ──
        if stripped.startswith("Subject:"):
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph(f"<b>{_esc(stripped)}</b>", styles["subject"]))
            story.append(HRFlowable(
                width="100%", thickness=0.4, color=HexColor("#999999"),
                spaceBefore=2 * mm, spaceAfter=5 * mm,
            ))
            i += 1
            continue

        # ── Dear Sir/Madam salutation ──
        if stripped.startswith("Dear "):
            story.append(Paragraph(_esc(stripped), styles["body"]))
            story.append(Spacer(1, 3 * mm))
            i += 1
            continue

        # ── Section headers (STATEMENT OF FACTS, LEGAL POSITION, etc.) ──
        if stripped.upper() in _SECTION_HEADERS:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph(_esc(stripped.upper()), styles["section"]))
            story.append(HRFlowable(
                width="100%", thickness=0.3, color=HexColor("#aaaaaa"),
                spaceBefore=0, spaceAfter=3 * mm,
            ))
            i += 1
            continue

        # ── Numbered "That" paragraphs (1. 2. etc.) — body text, not headings ──
        if re.match(r'^\d+\.\s', stripped):
            story.append(Paragraph(_md_to_rl(line), styles["body"]))
            i += 1
            continue

        # ── Lettered items: (a) (b) etc. ──
        if re.match(r'^\([a-z]\)', stripped):
            story.append(Paragraph(_md_to_rl(line), styles["list_item"]))
            i += 1
            continue

        # ── Sign-off: Yours faithfully, / Yours truly, / Sincerely, ──
        if stripped.lower() in ("yours faithfully,", "yours truly,", "sincerely,"):
            story.append(Spacer(1, 8 * mm))
            story.append(Paragraph(_esc(stripped), styles["body"]))
            i += 1
            continue

        # ── Sd/- signature marker ──
        if stripped == "Sd/-":
            story.append(Spacer(1, 6 * mm))
            story.append(Paragraph(_esc(stripped), styles["body_bold"]))
            i += 1
            continue

        # ── WARNING lines ──
        if "WARNING" in stripped.upper() or "URGENT" in stripped.upper():
            story.append(Paragraph(_md_to_rl(line), styles["warning"]))
            i += 1
            continue

        # ── Quoted statutory text ──
        if line.startswith("  [") and "]" in line:
            story.append(Paragraph(_md_to_rl(line), styles["legal_quote"]))
            i += 1
            continue

        # ── Bullet points ──
        if stripped.startswith("- ") or stripped.startswith("\u2022 "):
            bullet_text = stripped[2:]
            story.append(Paragraph(
                f"&bull;&nbsp;&nbsp;{_md_to_rl(bullet_text)}", styles["body"]
            ))
            i += 1
            continue

        # ── Default body text (convert any remaining **bold** to <b>) ──
        story.append(Paragraph(_md_to_rl(line), styles["body"]))
        i += 1

    # Lawyer attestation for ₹599 tier
    if is_lawyer_tier:
        story.append(Spacer(1, 10 * mm))
        story.append(HRFlowable(
            width="100%", thickness=0.5, color=HexColor("#2c3e50"),
            spaceBefore=2 * mm, spaceAfter=4 * mm,
        ))
        story.append(Paragraph(
            "ADVOCATE ATTESTATION",
            styles["heading"],
        ))
        story.append(Paragraph(
            "This legal notice has been reviewed, vetted, and approved by a licensed advocate "
            "enrolled with the Bar Council of India. The advocate confirms that the notice is "
            "legally sound, the cited statutory provisions are applicable, and the arguments "
            "presented are consistent with established consumer protection jurisprudence.",
            styles["body"],
        ))
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("Advocate Name: ___________________________", styles["body"]))
        story.append(Paragraph("Bar Council Enrollment No.: _______________", styles["body"]))
        story.append(Paragraph("Date of Review: ___________________________", styles["body"]))
        story.append(Paragraph("Signature: ________________________________", styles["body"]))

    # ── Annexures ────────────────────────────────────────────────
    if annexures:
        _append_annexures(story, styles, annexures)

    try:
        doc.build(story)
    except Exception as e:
        logger.error(f"Error generating PDF document: {e}", exc_info=True)
        # Ensure we don't crash the server hard, maybe raise a ValueError that can be caught
        raise ValueError(f"Failed to build PDF: {str(e)}") from e

    return buf.getvalue()


def _append_annexures(
    story: list,
    styles: dict[str, ParagraphStyle],
    annexures: list[tuple[str, str, bytes]],
) -> None:
    """Append uploaded evidence as annexure pages."""
    max_img_w = _PAGE_W - 2 * _MARGIN - 10 * mm
    max_img_h = _PAGE_H - 2 * _MARGIN - 40 * mm  # room for header

    story.append(PageBreak())
    story.append(Paragraph("ANNEXURES", styles["title"]))
    story.append(HRFlowable(
        width="100%", thickness=0.5, color=HexColor("#111111"),
        spaceBefore=1 * mm, spaceAfter=4 * mm,
    ))
    story.append(Paragraph(
        "The following documents are attached as supporting evidence "
        "and form an integral part of this legal notice.",
        styles["body"],
    ))
    story.append(Spacer(1, 4 * mm))

    for idx, (filename, content_type, data) in enumerate(annexures, 1):
        label = f"Annexure {idx}: {_esc(filename)}"

        if content_type.startswith("image/"):
            story.append(Paragraph(f"<b>{label}</b>", styles["heading"]))
            try:
                img = RLImage(io.BytesIO(data))
                iw, ih = img.drawWidth, img.drawHeight
                if iw > 0 and ih > 0:
                    scale = min(max_img_w / iw, max_img_h / ih, 1.0)
                    img.drawWidth = iw * scale
                    img.drawHeight = ih * scale
                story.append(img)
            except Exception as e:
                logger.error(f"Failed to embed image annexure '{filename}': {e}")
                story.append(Paragraph(
                    f"<i>[Image could not be embedded: {_esc(filename)}]</i>",
                    styles["small"],
                ))
            story.append(Spacer(1, 6 * mm))
        elif content_type == "application/pdf":
            story.append(Paragraph(f"<b>{label}</b>", styles["heading"]))
            story.append(Paragraph(
                f"[Attached PDF document: {_esc(filename)} — "
                f"{len(data):,} bytes]",
                styles["body"],
            ))
            story.append(Spacer(1, 6 * mm))
        else:
            story.append(Paragraph(f"<b>{label}</b>", styles["heading"]))
            story.append(Paragraph(
                f"[Attached file: {_esc(filename)} — {content_type}]",
                styles["body"],
            ))
            story.append(Spacer(1, 4 * mm))
