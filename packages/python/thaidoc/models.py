from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

DocumentSource = str | Path | bytes
ExtractionMode = Literal["rules", "ai", "auto"]
T = TypeVar("T")


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class FieldProvenance(BaseModel):
    page: int = Field(ge=1)
    bbox: BoundingBox | None = None
    method: Literal["digital_text", "ocr", "rule", "ai"]
    source_text: str | None = None


class ExtractedField(BaseModel, Generic[T]):
    value: T | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    provenance: list[FieldProvenance] = Field(default_factory=list)


class ExtractionOptions(BaseModel):
    mode: ExtractionMode = "auto"
    language: str = "tha+eng"
    ai_confidence_threshold: float = Field(default=0.65, ge=0, le=1)


class PageContent(BaseModel):
    page: int
    text: str
    method: Literal["digital_text", "ocr"]
    width: float | None = None
    height: float | None = None


class LoadedDocument(BaseModel):
    filename: str
    mime_type: str
    sha256: str
    pages: list[PageContent]


class ExtractionResult(BaseModel, Generic[T]):
    schema_name: str
    schema_version: str
    document: T
    fields: dict[str, ExtractedField[Any]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
