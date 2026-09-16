from __future__ import annotations

import hashlib
import io
import mimetypes
from pathlib import Path
from typing import cast

import pymupdf
from PIL import Image

from thaidoc.models import DocumentSource, LoadedDocument, PageContent
from thaidoc.normalize import normalize_thai_text
from thaidoc.ocr import ImagePreprocessingOptions, OCRProvider, TesseractOCRProvider, preprocess_image

SUPPORTED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}
DIGITAL_TEXT_MIN_CHARACTERS = 20
HYBRID_TEXT_MAX_CHARACTERS = 240
LARGE_IMAGE_PAGE_RATIO = 0.2


def _read_source(source: DocumentSource) -> tuple[bytes, str]:
    if isinstance(source, bytes):
        return source, "document"
    path = Path(source)
    return path.read_bytes(), path.name


def _mime_type(filename: str, content: bytes) -> str:
    if content.startswith(b"%PDF"):
        return "application/pdf"
    if content.startswith(b"\x89PNG"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def _has_large_embedded_image(page: pymupdf.Page) -> bool:
    page_area = max(float(page.rect.width * page.rect.height), 1.0)
    for image in page.get_images(full=True):  # type: ignore[no-untyped-call]
        xref = image[0]
        for rect in page.get_image_rects(xref):
            if float(rect.width * rect.height) / page_area >= LARGE_IMAGE_PAGE_RATIO:
                return True
    return False


def _render_page(page: pymupdf.Page) -> Image.Image:
    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),  # type: ignore[no-untyped-call]
        alpha=False,
    )
    with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:  # type: ignore[no-untyped-call]
        return cast(Image.Image, image.convert("RGB"))


def _merge_text_layers(digital_text: str, ocr_text: str) -> str:
    digital_lines = [line.strip() for line in digital_text.splitlines() if line.strip()]
    ocr_lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    seen = {line.casefold() for line in digital_lines}
    merged = list(digital_lines)
    for line in ocr_lines:
        key = line.casefold()
        if key not in seen:
            merged.append(line)
            seen.add(key)
    return "\n".join(merged)


def load_document(
    source: DocumentSource,
    *,
    ocr: OCRProvider | None = None,
    language: str = "tha+eng",
    preprocessing: ImagePreprocessingOptions | None = None,
) -> LoadedDocument:
    content, filename = _read_source(source)
    mime_type = _mime_type(filename, content)
    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError(f"Unsupported document type: {mime_type}")

    ocr = ocr or TesseractOCRProvider()
    pages: list[PageContent] = []
    if mime_type == "application/pdf":
        with pymupdf.open(stream=content, filetype="pdf") as pdf:  # type: ignore[no-untyped-call]
            if pdf.needs_pass:
                raise ValueError("Encrypted PDF files are not supported")
            for index, page in enumerate(pdf):
                digital_text = normalize_thai_text(page.get_text("text"))
                text = digital_text
                method = "digital_text"
                needs_ocr = len(digital_text) < DIGITAL_TEXT_MIN_CHARACTERS
                needs_hybrid = (
                    not needs_ocr
                    and len(digital_text) < HYBRID_TEXT_MAX_CHARACTERS
                    and _has_large_embedded_image(page)
                )
                if needs_ocr or needs_hybrid:
                    ocr_image = preprocess_image(_render_page(page), preprocessing)
                    ocr_text = normalize_thai_text(ocr.recognize(ocr_image, language=language))
                    if needs_hybrid and ocr_text:
                        text = _merge_text_layers(digital_text, ocr_text)
                        method = "hybrid"
                    elif needs_ocr:
                        text = ocr_text
                        method = "ocr"
                pages.append(
                    PageContent(
                        page=index + 1,
                        text=text,
                        method=method,
                        ocr_provider=ocr.name if method in {"ocr", "hybrid"} else None,
                        width=page.rect.width,
                        height=page.rect.height,
                    )
                )
    else:
        with Image.open(io.BytesIO(content)) as source_image:
            image = source_image.convert("RGB")
        ocr_image = preprocess_image(image, preprocessing)
        text = normalize_thai_text(ocr.recognize(ocr_image, language=language))
        pages.append(
            PageContent(
                page=1,
                text=text,
                method="ocr",
                ocr_provider=ocr.name,
                width=float(image.width),
                height=float(image.height),
            )
        )

    return LoadedDocument(
        filename=filename,
        mime_type=mime_type,
        sha256=hashlib.sha256(content).hexdigest(),
        pages=pages,
    )
