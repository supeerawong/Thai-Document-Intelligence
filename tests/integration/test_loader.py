import io

import fitz
from PIL import Image
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


class StubOCR:
    name = "stub"

    def __init__(self, text: str) -> None:
        self.text = text
        self.images: list[Image.Image] = []

    def recognize(self, image: Image.Image, *, language: str = "tha+eng") -> str:
        self.images.append(image.copy())
        return self.text


def test_mixed_page_merges_short_digital_layer_with_large_scanned_region() -> None:
    image = Image.new("RGB", (800, 1000), "white")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")

    pdf = fitz.open()
    page = pdf.new_page(width=600, height=800)
    page.insert_image(fitz.Rect(0, 0, 600, 800), stream=image_bytes.getvalue())
    page.insert_text((30, 30), "digital note kept on page")
    content = pdf.tobytes()
    pdf.close()

    provider = StubOCR("ข้อความจากภาพ")
    loaded = load_document(content, ocr=provider)

    assert loaded.pages[0].method == "hybrid"
    assert loaded.pages[0].ocr_provider == "stub"
    assert "digital note kept on page" in loaded.pages[0].text
    assert "ข้อความจากภาพ" in loaded.pages[0].text


def test_image_preprocessing_upscales_small_input() -> None:
    image = Image.new("RGB", (400, 300), "white")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    provider = StubOCR("ทดสอบ")

    loaded = load_document(image_bytes.getvalue(), ocr=provider)

    assert loaded.pages[0].ocr_provider == "stub"
    assert provider.images[0].width == 800
    assert provider.images[0].mode == "L"
