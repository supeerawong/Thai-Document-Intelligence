from __future__ import annotations

import hashlib
import io
import mimetypes
from pathlib import Path

import pymupdf
from PIL import Image

from thaidoc.models import DocumentSource, LoadedDocument, PageContent
from thaidoc.normalize import normalize_thai_text
from thaidoc.ocr import OCRProvider, TesseractOCRProvider

SUPPORTED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}


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


def load_document(
    source: DocumentSource,
    *,
    ocr: OCRProvider | None = None,
    language: str = "tha+eng",
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
                text = normalize_thai_text(page.get_text("text"))
                method = "digital_text"
                if len(text) < 20:
                    pixmap = page.get_pixmap(
                        matrix=pymupdf.Matrix(2, 2),  # type: ignore[no-untyped-call]
                        alpha=False,
                    )
                    ocr_image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                    text = normalize_thai_text(ocr.recognize(ocr_image, language=language))
                    method = "ocr"
                pages.append(
                    PageContent(
                        page=index + 1,
                        text=text,
                        method=method,
                        width=page.rect.width,
                        height=page.rect.height,
                    )
                )
    else:
        image = Image.open(io.BytesIO(content)).convert("RGB")
        text = normalize_thai_text(ocr.recognize(image, language=language))
        pages.append(
            PageContent(
                page=1,
                text=text,
                method="ocr",
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
