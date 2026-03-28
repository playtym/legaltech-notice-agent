import pytest
from legaltech.services.pdf_generator import generate_pdf

def test_generate_pdf_with_valid_content():
    notice_text = "LEGAL NOTICE\n\nDate: 2026-03-20\n\nSubject: Test Notice\n\nDear Sir/Madam,\nThis is a test notice."
    pdf_bytes = generate_pdf(notice_text)
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

def test_generate_pdf_with_empty_content():
    notice_text = ""
    pdf_bytes = generate_pdf(notice_text)
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

def test_generate_pdf_with_lawyer_tier():
    notice_text = "LEGAL NOTICE\n\nTest."
    pdf_bytes = generate_pdf(notice_text, is_lawyer_tier=True)
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

def test_generate_pdf_with_annexures():
    notice_text = "LEGAL NOTICE\n\nTest."
    valid_image = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    annexures = [
        ("test_doc.pdf", "application/pdf", b"%PDF-1.4..."),
        ("test_img.gif", "image/gif", valid_image),
        ("invalid_img.png", "image/png", b"not-an-image"),
    ]
    
    pdf_bytes = generate_pdf(notice_text, annexures=annexures)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")
