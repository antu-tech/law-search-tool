import tempfile
import os
from src.application.parsing_service import ParsingService


def test_parse_txt_like_pdf():
    import fitz
    svc = ParsingService()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Civil Code Article 184 tort liability")
    doc.save(path)
    doc.close()

    try:
        result = svc.parse(path, "test.pdf")
        assert result.title == "test.pdf"
        assert result.content_type == "pdf"
        assert any("Article" in c.text for c in result.chunks)
    finally:
        os.remove(path)
