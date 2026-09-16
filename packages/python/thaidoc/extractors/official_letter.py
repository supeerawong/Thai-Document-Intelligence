from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal

from thaidoc.classifiers import classify_official_document
from thaidoc.models import ExtractedField, ExtractionResult, FieldProvenance, LoadedDocument
from thaidoc.normalize import parse_thai_date
from thaidoc.schemas import Signer, ThaiOfficialLetter

SIGNER_POSITION_PREFIXES = (
    "ผู้อำนวยการ",
    "รองผู้อำนวยการ",
    "นักวิชาการ",
    "เจ้าพนักงาน",
    "เลขาธิการ",
    "อัยการ",
    "ประธาน",
    "กรรมการ",
    "หัวหน้า",
    "ผู้จัดการ",
)


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


def _signer_name(line: str) -> str | None:
    match = re.fullmatch(r"\(([^()\n]{2,100})\)", line.strip())
    if not match:
        return None
    name = match.group(1).strip()
    if len(name.split()) < 2 or any(character.isdigit() for character in name) or ":" in name:
        return None
    return name


def _extract_signers(text: str) -> list[Signer]:
    """Return signature blocks, including positions that wrap across lines."""
    lines = text.splitlines()
    signers: list[Signer] = []
    for index, line in enumerate(lines):
        name = _signer_name(line)
        if not name:
            continue

        position_lines: list[str] = []
        for following_line in lines[index + 1 :]:
            candidate = following_line.strip()
            if not candidate:
                continue
            if _signer_name(candidate):
                break
            if not candidate.startswith(SIGNER_POSITION_PREFIXES):
                break
            position_lines.append(candidate)
            if len(position_lines) == 3:
                break

        if position_lines:
            signers.append(Signer(name=name, position=" ".join(position_lines)))
    return signers


def extract_official_letter(document: LoadedDocument) -> ExtractionResult[ThaiOfficialLetter]:
    text = "\n".join(page.text for page in document.pages)
    document_type = classify_official_document(text)

    agency = _first_group(
        [r"^ส่วนราชการ\s+(.+)$", r"^([ก-๙A-Za-z].*(?:กระทรวง|กรม|สำนักงาน|มหาวิทยาลัย).*)$"],
        text,
    )
    contact = _first_group([r"^.*?((?:โทรศัพท์|โทร\.|อีเมล|E-mail)\s*.+)$"], text)
    if agency and contact and contact in agency:
        agency = agency[: agency.index(contact)].strip()
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
    signers = _extract_signers(text)

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
