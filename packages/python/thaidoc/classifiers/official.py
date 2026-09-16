import re

from thaidoc.schemas import DocumentType


def classify_official_document(text: str) -> DocumentType:
    if "บันทึกข้อความ" in text:
        return "internal_memo"
    if re.search(r"^คำสั่ง", text, re.MULTILINE):
        return "order"
    if re.search(r"^ประกาศ", text, re.MULTILINE):
        return "announcement"
    if "เรื่อง" in text and "เรียน" in text:
        return "external_letter"
    return "unknown"
