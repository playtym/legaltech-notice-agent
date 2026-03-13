"""PDF legal notice generator.

Produces a professionally formatted PDF letter suitable for serving
as a legal notice. Uses reportlab for zero-system-dependency PDF
generation (no wkhtmltopdf or WeasyPrint headless browser needed).
"""

from __future__ import annotations

import io
from datetime import date

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
    """Create a professional legal letter stylesheet."""
    base = getSampleStyleSheet()
    dark = HexColor("#1a1a1a")
    accent = HexColor("#2c3e50")

    return {
        "title": ParagraphStyle(
            "NoticeTitle",
            parent=base["Heading1"],
            fontSize=15,
            leading=20,
            alignment=TA_CENTER,
            textColor=accent,
            spaceAfter=4 * mm,
            fontName="Helvetica-Bold",
        ),
        "subtitle": ParagraphStyle(
            "SubTitle",
            parent=base["Normal"],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=HexColor("#555555"),
            spaceAfter=6 * mm,
            fontName="Helvetica",
        ),
        "heading": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontSize=11,
            leading=15,
            textColor=accent,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
            fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "BodyText",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            textColor=dark,
            spaceAfter=2 * mm,
            fontName="Helvetica",
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            textColor=dark,
            spaceAfter=2 * mm,
            fontName="Helvetica-Bold",
        ),
        "legal_quote": ParagraphStyle(
            "LegalQuote",
            parent=base["Normal"],
            fontSize=9,
            leading=12.5,
            alignment=TA_LEFT,
            textColor=HexColor("#333333"),
            leftIndent=12 * mm,
            rightIndent=8 * mm,
            spaceAfter=2 * mm,
            fontName="Helvetica-Oblique",
            borderColor=HexColor("#cccccc"),
            borderWidth=0,
            borderPadding=0,
        ),
        "small": ParagraphStyle(
            "SmallText",
            parent=base["Normal"],
            fontSize=8,
            leading=10,
            textColor=HexColor("#888888"),
            fontName="Helvetica",
        ),
        "address": ParagraphStyle(
            "Address",
            parent=base["Normal"],
            fontSize=10,
            leading=13,
            textColor=dark,
            fontName="Helvetica",
        ),
        "warning": ParagraphStyle(
            "Warning",
            parent=base["Normal"],
            fontSize=10,
            leading=13,
            textColor=HexColor("#c0392b"),
            fontName="Helvetica-Bold",
            spaceAfter=2 * mm,
        ),
    }


def _footer(canvas, doc):
    """Draw page number and confidential footer."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(HexColor("#999999"))
    canvas.drawCentredString(
        _PAGE_W / 2, 1.2 * cm,
        f"Page {doc.page} — CONFIDENTIAL & PRIVILEGED — For addressee only"
    )
    canvas.restoreState()


def _esc(text: str) -> str:
    """Escape XML special characters for reportlab Paragraph."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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

    story: list = []
    lines = notice_text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            story.append(Spacer(1, 2 * mm))
            i += 1
            continue

        # Title line
        if line.startswith("LEGAL NOTICE"):
            story.append(Paragraph(_esc(line), styles["title"]))
            story.append(HRFlowable(
                width="100%", thickness=0.5, color=HexColor("#2c3e50"),
                spaceBefore=1 * mm, spaceAfter=4 * mm,
            ))
            i += 1
            continue

        # Date line
        if line.startswith("Date:"):
            story.append(Paragraph(_esc(line), styles["body"]))
            story.append(Spacer(1, 3 * mm))
            i += 1
            continue

        # Address blocks (To, / From,)
        if line in ("To,", "From,"):
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph(f"<b>{_esc(line)}</b>", styles["address"]))
            i += 1
            # Collect address lines until blank
            while i < len(lines) and lines[i].strip():
                story.append(Paragraph(_esc(lines[i].strip()), styles["address"]))
                i += 1
            continue

        # Subject line
        if line.startswith("Subject:"):
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph(f"<b>{_esc(line)}</b>", styles["body_bold"]))
            story.append(HRFlowable(
                width="100%", thickness=0.3, color=HexColor("#cccccc"),
                spaceBefore=2 * mm, spaceAfter=4 * mm,
            ))
            i += 1
            continue

        # Numbered section headers (e.g. "1. Facts and grievance")
        if len(line) > 2 and line[0].isdigit() and ". " in line[:5]:
            story.append(Paragraph(_esc(line), styles["heading"]))
            i += 1
            continue

        # Section headers without numbers
        if line.endswith(":") and len(line) < 60:
            story.append(Paragraph(f"<b>{_esc(line)}</b>", styles["body_bold"]))
            i += 1
            continue

        # WARNING lines
        if "WARNING" in line or "URGENT" in line or "TIME-BARRED" in line:
            story.append(Paragraph(_esc(line), styles["warning"]))
            i += 1
            continue

        # Quoted statutory text
        if line.startswith("  [") and "]" in line:
            story.append(Paragraph(_esc(line), styles["legal_quote"]))
            i += 1
            continue

        # Bullet points
        if line.startswith("- ") or line.startswith("• "):
            bullet_text = line[2:]
            story.append(Paragraph(
                f"&bull;&nbsp;&nbsp;{_esc(bullet_text)}", styles["body"]
            ))
            i += 1
            continue

        # Sub-bullets (indented)
        if line.startswith("    ") and (line.strip().startswith("✓") or line.strip().startswith("✗") or line.strip().startswith("-")):
            story.append(Paragraph(
                f"&nbsp;&nbsp;&nbsp;&nbsp;{_esc(line.strip())}", styles["small"]
            ))
            i += 1
            continue

        # Sign-off
        if line == "Sincerely,":
            story.append(Spacer(1, 8 * mm))
            story.append(Paragraph(_esc(line), styles["body"]))
            i += 1
            # Name follows
            if i < len(lines) and lines[i].strip():
                story.append(Spacer(1, 12 * mm))
                story.append(Paragraph(f"<b>{_esc(lines[i].strip())}</b>", styles["body_bold"]))
                i += 1
            continue

        # Default body text
        story.append(Paragraph(_esc(line), styles["body"]))
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

    doc.build(story)
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
        width="100%", thickness=0.5, color=HexColor("#2c3e50"),
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
            except Exception:
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
