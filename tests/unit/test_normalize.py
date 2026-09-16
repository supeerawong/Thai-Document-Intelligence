from thaidoc.normalize import normalize_thai_text, parse_thai_date, thai_digits_to_arabic


def test_thai_digits_to_arabic() -> None:
    assert thai_digits_to_arabic("ที่ ๑๒/๒๕๖๙") == "ที่ 12/2569"


def test_normalize_removes_invisible_and_extra_whitespace() -> None:
    assert normalize_thai_text("เรื่อง\u200b   ทดสอบ\n\n\nเรียน") == "เรื่อง ทดสอบ\n\nเรียน"


def test_parse_buddhist_date() -> None:
    parsed = parse_thai_date("16 กันยายน 2569")
    assert parsed.iso == "2026-09-16"
    assert parsed.calendar == "buddhist"


def test_invalid_date_is_not_invented() -> None:
    assert parse_thai_date("31 กุมภาพันธ์ 2569").iso is None
