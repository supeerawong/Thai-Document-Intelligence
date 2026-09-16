import fitz
from fastapi.testclient import TestClient
from thaidoc import __version__
from thaidoc_api.main import app


def make_pdf() -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Official letter sample with enough embedded text for extraction.")
    content = pdf.tobytes()
    pdf.close()
    return content


def test_health_and_discovery() -> None:
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/v1/schemas").json()[0]["name"] == "thai_official_letter"
        assert client.get("/openapi.json").json()["info"]["version"] == __version__


def test_sync_extraction_contract() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/extractions",
            files={"file": ("sample.pdf", make_pdf(), "application/pdf")},
            data={"execution": "sync", "mode": "rules"},
        )
    assert response.status_code == 200, response.text
    assert response.json()["schema_name"] == "thai_official_letter"


def test_invalid_upload_uses_problem_json() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/extractions", files={"file": ("bad.txt", b"bad", "text/plain")})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "invalid_document"
