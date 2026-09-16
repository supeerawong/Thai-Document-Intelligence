<p align="center"><img src="assets/logo-full.svg" alt="Thai Document Intelligence" width="620"></p>

<p align="center"><strong>Extract structured, verifiable data from Thai documents.</strong><br>แปลงเอกสารภาษาไทยเป็นข้อมูลที่ตรวจสอบย้อนกลับได้</p>

<p align="center">
  <a href="LICENSE"><img alt="Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-4338CA">
  <img alt="Version 0.1" src="https://img.shields.io/badge/version-0.1-F59E0B">
</p>

Thai Document Intelligence (`thaidoc`) is an offline-first Python library and self-hosted service that turns Thai PDF and image documents into typed JSON. It understands Thai digits, Buddhist Era dates, OCR noise, and official-document fields. Every important field includes confidence and source provenance.

## Why thaidoc?

- **Works offline:** rules and Tesseract are the default path; no API key is required.
- **Verifiable:** extracted fields point back to their page, method, and source text.
- **Thai-aware:** normalization covers Thai digits, dates, and common official-letter labels.
- **Product-ready:** use the Python API, CLI, REST API, Ionic web app, or TypeScript SDK.
- **AI optional:** provider interfaces allow low-confidence results to be enhanced without coupling the core to a vendor.

```json
{
  "schema_name": "thai_official_letter",
  "document": {
    "document_type": "external_letter",
    "document_number": "อส 0000/1234",
    "date": { "original": "16 กันยายน 2569", "iso": "2026-09-16", "calendar": "buddhist" },
    "subject": "ขอเชิญประชุม",
    "recipient": "ผู้อำนวยการ...",
    "confidence": 0.8
  },
  "fields": {
    "subject": { "confidence": 0.95, "provenance": [{ "page": 1, "method": "rule", "source_text": "ขอเชิญประชุม" }] }
  }
}
```

## Quick start / เริ่มใช้งาน

```bash
git clone https://github.com/<owner>/thai-document-intelligence
cd thai-document-intelligence
docker compose up --build
```

Open the web app at `http://localhost:3000` and OpenAPI docs at `http://localhost:8000/docs`.

เปิดเว็บที่ `http://localhost:3000` แล้วลาก PDF, PNG หรือ JPEG เพื่อดู structured JSON พร้อม provenance ได้ทันที ข้อมูลต้นฉบับและผลลัพธ์มีอายุเริ่มต้น 24 ชั่วโมง

### Python

```bash
pip install -e .
```

```python
from thaidoc import extract
from thaidoc.schemas import ThaiOfficialLetter

result = extract("document.pdf", schema=ThaiOfficialLetter, mode="auto")
print(result.model_dump_json(indent=2))
```

### CLI

```bash
thaidoc extract document.pdf --schema thai_official_letter
thaidoc extract document.pdf --mode auto --output result.json
thaidoc serve
```

## Supported inputs

| Input | v0.1 | Processing |
|---|---:|---|
| Digital PDF | Yes | PyMuPDF text extraction |
| Scanned PDF | Yes | Tesseract `tha+eng` |
| Mixed PDF | Yes | Per-page text/OCR detection |
| PNG / JPEG | Yes | Tesseract `tha+eng` |
| DOCX | Planned | v0.4 |

The initial `thai_official_letter` schema covers external letters, internal memoranda, orders, and announcements. Missing values remain `null`; the extractor never invents a value.

### Optional AI provider

Set `THAIDOC_AI_BASE_URL` and `THAIDOC_AI_MODEL` to enable any OpenAI-compatible endpoint, including an Ollama `/v1` endpoint. `THAIDOC_AI_API_KEY` is optional. AI is used only for `mode=ai` or as a configured low-confidence fallback in `mode=auto`; the default installation makes no model request.

## REST API

```bash
curl -F "file=@document.pdf" -F "execution=auto" http://localhost:8000/v1/extractions
```

Documents up to five pages and 10 MiB run synchronously by default. Larger documents return a job ID and run through Redis/arq. The upload limit is 50 MiB and 200 pages. See [the API contract](docs/api/openapi.md).

## Architecture

```text
Document → Loader → Text/OCR → Thai normalization → Rule extraction
                                                       │
                                  optional AI fallback ◄┘
                                                       ↓
                                   validation + provenance → JSON
```

See [architecture](docs/architecture/overview.md), [schema](docs/schemas/thai-official-letter.md), and [roadmap](docs/ROADMAP.md).

## Privacy and security

The default extraction path is local and sends no telemetry. Source files and results expire after 24 hours unless configured otherwise. AI providers are opt-in. Never place secrets in documents or logs; see [SECURITY.md](SECURITY.md).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), choose a scoped item from the [first 20 issues](docs/initial-issues.md), and open a focused pull request. Several tasks are marked `good first issue`.

## Important notice

This project is independent open-source software and is not affiliated with or endorsed by any Thai government agency. Extracted data may contain errors and must be reviewed by a qualified person before legal, regulatory, financial, or other consequential use.

Licensed under [Apache-2.0](LICENSE).
