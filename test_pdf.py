import sys
sys.path.append('src')

try:
    from legaltech.services.pdf_generator import generate_pdf
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test():
    notice_text = "This is a test legal notice.\n\nIt works."
    try:
        pdf_bytes = generate_pdf(notice_text, is_lawyer_tier=False)
        with open('test_output.pdf', 'wb') as f:
            f.write(pdf_bytes)
        print("PDF generated successfully, size:", len(pdf_bytes))
    except Exception as e:
        print(f"Error generating PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test()
