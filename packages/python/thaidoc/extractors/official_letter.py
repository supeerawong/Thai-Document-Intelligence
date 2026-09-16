from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal

from thaidoc.classifiers import classify_official_document
from thaidoc.models import ExtractedField, ExtractionResult, FieldProvenance, LoadedDocument
from thaidoc.normalize import parse_thai_date
from thaidoc.schemas import Signer, ThaiOfficialLetter


def _match(pattern: str, text: str, *, flags: int = re.MULTILINE) -> re.Match[str] | None:
    return re.search(pattern, text, flags)


def _provenance(
    document: LoadedDocument,
    value: str,
    method: Literal["digital_text", "ocr", "rule", "ai"] = "rule",
) -> list[FieldProvenance]:
    for page in document.pages:
        if value and value in page.text:
            return [
                FieldProvenance(
                    page=page.page,
                    method=method,
                    source_text=value,
                )
            ]
    return []


def _field(document: LoadedDocument, value: object, confidence: float) -> ExtractedField[object]:
    text = value if isinstance(value, str) else ""
    return ExtractedField(value=value, confidence=confidence, provenance=_provenance(document, text))


def _first_group(patterns: Iterable[str], text: str) -> str | None:
    for pattern in patterns:
        match = _match(pattern, text)
        if match:
            return match.group(1).strip(" \t:-")
    return None


def extract_official_letter(document: LoadedDocument) -> ExtractionResult[ThaiOfficialLetter]:
    text = "\n".join(page.text for page in document.pages)
    document_type = classify_official_document(text)

    agency = _first_group(
        [r"^ส่วนราชการ\s+(.+)$", r"^([ก-๙A-Za-z].*(?:กระทรวง|กรม|สำนักงาน|มหาวิทยาลัย).*)$"],
        text,
    )
    number = _first_group([r"^(?:ที่)\s+([^\n]+)$"], text)
    date_text = _first_group(
        [
            r"(?:วันที่|^ที่\s*)?\s*(\d{1,2}\s+(?:มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม|[ก-ฮ]\.[ก-ฮ]\.?)\s+\d{4})"
        ],
        text,
    )
    subject = _first_group([r"^เรื่อง\s+(.+)$"], text)
    recipient = _first_group([r"^เรียน\s+(.+)$"], text)
    reference = _first_group([r"^อ้างถึง\s+(.+)$"], text)
    attachment = _first_group([r"^สิ่งที่ส่งมาด้วย\s+(.+)$"], text)
    contact = _first_group([r"^(.+(?:โทรศัพท์|โทร\.|อีเมล|E-mail).+)$"], text)

    signer_matches = re.findall(r"\(([^()\n]{2,100})\)\s*\n([^\n]{2,150})", text)
    signers = [Signer(name=name.strip(), position=position.strip()) for name, position in signer_matches]

    body_start = None
    if recipient:
        position = text.find(recipient)
        body_start = text.find("\n", position)
    body = text[body_start + 1 :].strip() if body_start is not None and body_start >= 0 else text

    values = [agency, number, date_text, subject, recipient]
    confidence = round(sum(item is not None for item in values) / len(values), 2)
    letter = ThaiOfficialLetter(
        document_type=document_type,
        agency=agency,
        document_number=number,
        date=parse_thai_date(date_text) if date_text else None,
        subject=subject,
        recipient=recipient,
        references=[reference] if reference else [],
        attachments=[attachment] if attachment else [],
        body=body or None,
        signers=signers,
        contact=contact,
        page_count=len(document.pages),
        confidence=confidence,
    )
    fields = {
        "agency": _field(document, agency, 0.9 if agency else 0),
        "document_number": _field(document, number, 0.95 if number else 0),
        "date": _field(document, date_text, 0.95 if date_text else 0),
        "subject": _field(document, subject, 0.95 if subject else 0),
        "recipient": _field(document, recipient, 0.95 if recipient else 0),
    }
    warnings = [f"Could not extract {name}" for name, field in fields.items() if field.value is None]
    return ExtractionResult(
        schema_name="thai_official_letter",
        schema_version="1.0.0",
        document=letter,
        fields=fields,
        warnings=warnings,
    )
