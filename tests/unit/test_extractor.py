from thaidoc.extractors import extract_official_letter
from thaidoc.models import LoadedDocument, PageContent

TEXT = """สำนักงานทดสอบ
ที่ อส 0000/1234
16 กันยายน 2569
เรื่อง ขอเชิญประชุม
เรียน ผู้อำนวยการสำนักทดสอบ
อ้างถึง หนังสือเลขที่ 1
สิ่งที่ส่งมาด้วย กำหนดการประชุม
จึงเรียนมาเพื่อโปรดพิจารณา
(สมชาย ใจดี)
ผู้อำนวยการสำนักงานทดสอบ
โทรศัพท์ 02-000-0000"""


def test_extract_official_letter_with_provenance() -> None:
    loaded = LoadedDocument(
        filename="sample.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[PageContent(page=1, text=TEXT, method="digital_text")],
    )
    result = extract_official_letter(loaded)
    assert result.document.document_type == "external_letter"
    assert result.document.subject == "ขอเชิญประชุม"
    assert result.document.date and result.document.date.iso == "2026-09-16"
    assert result.fields["subject"].provenance[0].page == 1
    assert result.document.signers[0].name == "สมชาย ใจดี"


def test_missing_fields_are_null_and_warned() -> None:
    loaded = LoadedDocument(
        filename="empty.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[PageContent(page=1, text="ข้อความทั่วไป", method="digital_text")],
    )
    result = extract_official_letter(loaded)
    assert result.document.subject is None
    assert "Could not extract subject" in result.warnings


def test_internal_memo_separates_contact_and_ignores_parenthetical_body_text() -> None:
    text = """บันทึกข้อความ
ส่วนราชการ สำนักเทคโนโลยีสารสนเทศและการสื่อสาร โทร. 0 2000 0000
ที่ อส 0001/99
วันที่ 13 มกราคม 2569
เรื่อง ขอทดสอบระบบ
เรียน เลขาธิการสำนักงานทดสอบ
รายละเอียดประกอบการพิจารณา (เอกสารแนบ 1)
(ONLINE)
อัยการสูงสุดปฏิบัติตามหน้าที่
(เอกสารแนบ 2)
ผู้อำนวยการสำนักงานอัยการสูงสุด
(นายสมชาย ใจดี)
นักวิชาการคอมพิวเตอร์ปฏิบัติการ
(นางสาวสมหญิง ใจงาม)
ผู้อำนวยการสำนักทดสอบ"""
    loaded = LoadedDocument(
        filename="internal-memo.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[PageContent(page=1, text=text, method="digital_text")],
    )

    result = extract_official_letter(loaded)

    assert result.document.document_type == "internal_memo"
    assert result.document.agency == "สำนักเทคโนโลยีสารสนเทศและการสื่อสาร"
    assert result.document.contact == "โทร. 0 2000 0000"
    assert [signer.name for signer in result.document.signers] == [
        "นายสมชาย ใจดี",
        "นางสาวสมหญิง ใจงาม",
    ]
