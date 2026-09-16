import fitz
from thaidoc.loaders import load_document


def test_load_digital_pdf_from_bytes() -> None:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "This is enough embedded text for digital extraction.")
    content = pdf.tobytes()
    pdf.close()
    loaded = load_document(content)
    assert loaded.pages[0].method == "digital_text"
    assert "embedded text" in loaded.pages[0].text


def test_reject_unknown_bytes() -> None:
    import pytest

    with pytest.raises(ValueError, match="Unsupported"):
        load_document(b"not a document")
