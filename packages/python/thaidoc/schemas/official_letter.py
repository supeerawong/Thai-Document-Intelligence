from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DocumentType = Literal["external_letter", "internal_memo", "order", "announcement", "unknown"]


class ThaiDocumentDate(BaseModel):
    original: str
    iso: str | None = None
    calendar: Literal["buddhist", "gregorian", "unknown"] = "unknown"


class Signer(BaseModel):
    name: str | None = None
    position: str | None = None
    acting_status: str | None = None


class ThaiOfficialLetter(BaseModel):
    document_type: DocumentType = "unknown"
    agency: str | None = None
    document_number: str | None = None
    date: ThaiDocumentDate | None = None
    subject: str | None = None
    recipient: str | None = None
    references: list[str] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)
    body: str | None = None
    signers: list[Signer] = Field(default_factory=list)
    contact: str | None = None
    page_count: int = Field(ge=1)
    confidence: float = Field(default=0, ge=0, le=1)
