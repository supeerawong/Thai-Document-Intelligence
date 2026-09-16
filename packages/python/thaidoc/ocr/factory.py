from __future__ import annotations

from importlib.util import find_spec
from typing import Literal

from thaidoc.ocr.base import OCRProvider
from thaidoc.ocr.paddle import PaddleOCRProvider
from thaidoc.ocr.tesseract import TesseractOCRProvider

OCRProviderName = Literal["tesseract", "paddle"]


def create_ocr_provider(name: str) -> OCRProvider:
    normalized = name.strip().lower()
    if normalized == "tesseract":
        return TesseractOCRProvider()
    if normalized == "paddle":
        return PaddleOCRProvider()
    raise ValueError(f"Unsupported OCR provider: {name}")


def available_ocr_providers() -> list[str]:
    providers = ["tesseract"]
    if find_spec("paddleocr") is not None:
        providers.append("paddle")
    return providers
