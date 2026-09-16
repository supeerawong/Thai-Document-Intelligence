from __future__ import annotations

import re
import unicodedata
from datetime import date

from thaidoc.schemas import ThaiDocumentDate

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
MONTHS = {
    "มกราคม": 1,
    "ม.ค.": 1,
    "มค": 1,
    "กุมภาพันธ์": 2,
    "ก.พ.": 2,
    "กพ": 2,
    "มีนาคม": 3,
    "มี.ค.": 3,
    "มีค": 3,
    "เมษายน": 4,
    "เม.ย.": 4,
    "เมย": 4,
    "พฤษภาคม": 5,
    "พ.ค.": 5,
    "พค": 5,
    "มิถุนายน": 6,
    "มิ.ย.": 6,
    "มิย": 6,
    "กรกฎาคม": 7,
    "ก.ค.": 7,
    "กค": 7,
    "สิงหาคม": 8,
    "ส.ค.": 8,
    "สค": 8,
    "กันยายน": 9,
    "ก.ย.": 9,
    "กย": 9,
    "ตุลาคม": 10,
    "ต.ค.": 10,
    "ตค": 10,
    "พฤศจิกายน": 11,
    "พ.ย.": 11,
    "พย": 11,
    "ธันวาคม": 12,
    "ธ.ค.": 12,
    "ธค": 12,
}


def thai_digits_to_arabic(value: str) -> str:
    return value.translate(THAI_DIGITS)


def normalize_thai_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value).replace("\u200b", "").replace("\ufeff", "")
    value = thai_digits_to_arabic(value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def parse_thai_date(value: str) -> ThaiDocumentDate:
    original = value.strip()
    normalized = thai_digits_to_arabic(original)
    match = re.search(r"(\d{1,2})\s+([^\s]+)\s+(\d{4})", normalized)
    if not match:
        return ThaiDocumentDate(original=original)
    day, month_text, year_text = match.groups()
    month = MONTHS.get(month_text)
    year = int(year_text)
    calendar = "buddhist" if year >= 2400 else "gregorian"
    gregorian_year = year - 543 if calendar == "buddhist" else year
    if not month:
        return ThaiDocumentDate(original=original, calendar=calendar)
    try:
        iso = date(gregorian_year, month, int(day)).isoformat()
    except ValueError:
        iso = None
    return ThaiDocumentDate(original=original, iso=iso, calendar=calendar)
