from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel

from thaidoc.extractors import extract_official_letter
from thaidoc.loaders import load_document
from thaidoc.models import DocumentSource, ExtractionMode, ExtractionOptions, ExtractionResult
from thaidoc.ocr import ImagePreprocessingOptions, OCRProvider
from thaidoc.providers import StructuredExtractionProvider
from thaidoc.schemas import ThaiOfficialLetter


def extract(
    source: DocumentSource,
    *,
    schema: type[BaseModel] = ThaiOfficialLetter,
    mode: str = "auto",
    provider: StructuredExtractionProvider | None = None,
    ocr: OCRProvider | None = None,
    preprocessing: ImagePreprocessingOptions | None = None,
) -> ExtractionResult[Any]:
    options = ExtractionOptions(mode=cast(ExtractionMode, mode))
    document = load_document(source, ocr=ocr, language=options.language, preprocessing=preprocessing)
    if schema is not ThaiOfficialLetter:
        raise ValueError(f"Unsupported schema: {schema.__name__}")
    result = extract_official_letter(document)
    if options.mode == "ai" and provider is None:
        raise ValueError("AI mode requires a structured extraction provider")
    if (
        provider
        and options.mode in {"ai", "auto"}
        and (options.mode == "ai" or result.document.confidence < options.ai_confidence_threshold)
    ):
        ai_data = provider.extract("\n".join(page.text for page in document.pages), schema)
        result.document = schema.model_validate(ai_data)
        result.warnings.append(f"Low-confidence fields were processed by {provider.name}")
    return result
