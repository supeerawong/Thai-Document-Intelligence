# Thai Document Intelligence — Repository Design Plan

## 1. Product Summary

**ชื่อโปรเจกต์:** Thai Document Intelligence  
**Repository:** `thai-document-intelligence`  
**Python package / import / CLI:** `thaidoc`  
**TypeScript SDK:** `@thaidoc/sdk`  
**License:** Apache-2.0

**Tagline**

> Extract structured, verifiable data from Thai documents.  
> แปลงเอกสารภาษาไทยเป็นข้อมูลที่ตรวจสอบย้อนกลับได้

ผลิตภัณฑ์เป็น library-first monorepo สำหรับแปลง PDF และรูปภาพภาษาไทยเป็น structured JSON โดย v0.1 เน้นหนังสือราชการไทย ทำงานได้โดยไม่ต้องใช้ cloud AI และเพิ่ม OpenAI-compatible/Ollama เพื่อช่วย extraction ได้ตามต้องการ

### Logo concept

- สัญลักษณ์กระดาษมุมพับ ผสานอักษรไทย `ก` และจุดเชื่อมสามจุดที่สื่อถึง structured data
- รูปทรงต้องอ่านออกในขนาด GitHub avatar 32×32 px และไม่ใช้ตราครุฑหรือสัญลักษณ์ราชการ
- สีหลัก: Indigo `#4338CA`, Thai Gold `#F59E0B`, Slate `#0F172A`, Off-white `#F8FAFC`
- Wordmark: “Thai Document Intelligence”; ชื่อย่อ `TDI`
- ส่งมอบเป็น SVG เต็ม, icon-only SVG และ PNG ขนาด 512/128/32 px

## 2. Architecture and Repository

### Processing flow

```text
PDF / PNG / JPEG
        │
        ▼
Document Loader ──► digital-text / scanned / mixed-page detection
        │
        ▼
Text Extraction or Tesseract OCR (tha+eng)
        │
        ▼
Thai Normalization + Layout Reconstruction
        │
        ▼
Document Classification
        │
        ▼
Rule-based Schema Extraction
        │
        ├── optional low-confidence fallback
        ▼
OpenAI-compatible / Ollama Provider
        │
        ▼
Validation + Confidence + Field Provenance
        │
        ▼
JSON / CLI / REST API / Ionic Web / SDK
```

ทุก field สำคัญต้องมี provenance ได้แก่หน้า, bounding box เมื่อมี, extraction method และ confidence เพื่อไม่ให้ผล AI เป็น black box

### Repository structure

```text
thai-document-intelligence/
├─ apps/
│  ├─ api/                    # FastAPI transport and dependency wiring
│  ├─ worker/                 # arq worker and retention cleanup
│  └─ web/                    # Ionic 9 + Angular 22 web/PWA
├─ packages/
│  ├─ python/thaidoc/
│  │  ├─ loaders/
│  │  ├─ ocr/
│  │  ├─ normalize/
│  │  ├─ layout/
│  │  ├─ classifiers/
│  │  ├─ extractors/
│  │  ├─ providers/
│  │  ├─ schemas/
│  │  └─ cli/
│  └─ typescript-sdk/
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ contract/
│  ├─ golden/
│  └─ fixtures/synthetic/
├─ docs/
│  ├─ architecture/
│  ├─ api/
│  ├─ schemas/
│  └─ contributing/
├─ examples/
├─ infra/docker/
├─ .github/
│  ├─ workflows/
│  └─ ISSUE_TEMPLATE/
├─ docker-compose.yml
├─ pyproject.toml
├─ README.md
├─ CONTRIBUTING.md
├─ SECURITY.md
├─ CODE_OF_CONDUCT.md
└─ LICENSE
```

Python รองรับ `>=3.11`; dependencies ล็อกด้วย `uv`. Frontend ใช้ Ionic 9 และ Angular 22 standalone components โดยล็อก latest stable patch ตอน scaffold—ปัจจุบัน Ionic docs อยู่ที่ v9 และ Angular v22 อยู่ใน active support ([Ionic](https://ionicframework.com/docs), [Angular releases](https://angular.dev/reference/releases)).

### Runtime components

- FastAPI และ Pydantic v2 สำหรับ HTTP/OpenAPI
- PyMuPDF สำหรับ PDF/text/layout เบื้องต้น
- Tesseract 5 `tha+eng` เป็น OCR เริ่มต้น; PaddleOCR เป็น provider เสริมใน v0.2
- SQLAlchemy 2 + Alembic
- SQLite เป็นค่าเริ่มต้น; PostgreSQL รองรับก่อน v1.0
- Redis + `arq` สำหรับงาน async
- local filesystem เป็น artifact store; S3-compatible storage เพิ่มภายหลัง
- ไม่มี telemetry โดยค่าเริ่มต้น

## 3. Public Interfaces, Database, and API

### Python API

```python
from thaidoc import extract
from thaidoc.schemas import ThaiOfficialLetter

result = extract(
    "document.pdf",
    schema=ThaiOfficialLetter,
    mode="auto",  # rules | ai | auto
    provider=None,
)
```

Public types:

- `DocumentSource`
- `ExtractionOptions`
- `ExtractionResult[T]`
- `ExtractedField[T]`
- `FieldProvenance`
- `OCRProvider`
- `StructuredExtractionProvider`
- `ThaiOfficialLetter`

CLI:

```bash
thaidoc extract document.pdf --schema thai_official_letter
thaidoc extract document.pdf --mode auto --output result.json
thaidoc serve
```

### Initial document schema

`ThaiOfficialLetter` ประกอบด้วย:

- `document_type`: `external_letter | internal_memo | order | announcement | unknown`
- `agency`
- `document_number`
- `date.original`, `date.iso`, `date.calendar`
- `subject`
- `recipient`
- `references[]`
- `attachments[]`
- `body`
- `signers[]`: name, position, acting status
- `contact`
- `page_count`
- `confidence`
- `fields.<name>.provenance[]`
- `warnings[]`

ค่าที่หาไม่พบใช้ `null` ไม่สร้างข้อมูลเดา และ validation warning ไม่ทำให้ผลลัพธ์ทั้งฉบับล้มเหลว

### REST API v1

- `POST /v1/extractions`
  - Multipart: `file`, `schema`, `mode`, `execution`
  - `execution`: `auto | sync | async`
  - `auto` ใช้ sync เมื่อไม่เกิน 5 หน้าและ 10 MiB; นอกนั้นใช้ async
  - ตอบ `200 ExtractionResult` หรือ `202 Job`
- `GET /v1/jobs/{job_id}` — `queued | processing | succeeded | failed | expired`
- `GET /v1/jobs/{job_id}/result`
- `DELETE /v1/jobs/{job_id}` — ลบ metadata, result และ artifacts
- `GET /v1/schemas`
- `GET /v1/capabilities` — OCR/AI providers ที่เปิดใช้
- `GET /health/live`
- `GET /health/ready`

ข้อจำกัดเริ่มต้น: 50 MiB, 200 หน้า, PDF/PNG/JPEG หากบังคับ sync เกิน threshold ให้ตอบ `422 sync_limit_exceeded`

ข้อผิดพลาดใช้ `application/problem+json` พร้อม `type`, `title`, `status`, `code`, `detail`, `request_id` และ field errors โดยไม่คืน stack trace

### Database and retention

ตารางหลัก:

- `documents`: id, SHA-256, filename, MIME type, size, page count, timestamps, expiry
- `extraction_jobs`: document id, schema, mode, execution, status, progress, error code, timestamps
- `extraction_results`: job id, schema version, result JSON, confidence, warnings
- `artifacts`: document/job id, kind, storage key, checksum, size, expiry
- `provider_runs`: job id, provider/model, latency, token counts, sanitized error; ไม่เก็บ API key

ไฟล์และผลลัพธ์มี TTL เริ่มต้น 24 ชั่วโมง ปรับผ่าน environment ได้ และ worker ลบทั้ง DB records กับ artifacts ที่หมดอายุ รองรับ idempotency ผ่าน `Idempotency-Key` และ SHA-256 โดยไม่ deduplicate ข้ามคำขอหาก option/schema ต่างกัน

API bind เฉพาะ localhost โดยค่าเริ่มต้น; shared API key เป็น optional deployment setting ไม่มี account, workspace หรือ RBAC ใน v1.0

## 4. README.md Specification

README เป็นภาษาอังกฤษเป็นหลัก พร้อมคำอธิบายและ quick start ภาษาไทย โดยเรียงเนื้อหาดังนี้:

1. Logo, tagline, badges และ screenshot/GIF
2. ปัญหาที่แก้: Thai dates, Buddhist Era, Thai digits, OCR noise, official-document layout
3. จุดเด่น: offline-first, AI optional, provenance, self-hosted, typed schemas
4. ตัวอย่าง input → JSON output
5. Quick start:

```bash
git clone https://github.com/<owner>/thai-document-intelligence
cd thai-document-intelligence
docker compose up --build
```

เปิด `http://localhost:3000` และ API docs ที่ `http://localhost:8000/docs`

6. Python installation และ API example
7. CLI usage
8. Supported documents/formats matrix
9. AI provider configuration โดยย้ำว่าไม่ต้องมี API keyสำหรับ default path
10. Architecture diagram
11. Privacy/security และ TTL
12. Roadmap
13. Contributing และลิงก์ `good first issue`
14. License และ acknowledgment

README ต้องระบุชัดว่าโปรเจกต์ไม่ใช่บริการของหน่วยงานรัฐ และผล extraction ต้องได้รับการตรวจสอบก่อนใช้กับงานที่มีผลทางกฎหมาย

## 5. Roadmap

- **v0.1 — Official Letter MVP:** PDF/image loader, digital text + Tesseract OCR, Thai normalization, dates/numbers, official-letter schema, provenance/confidence, CLI, REST sync/async, Ionic upload/results UI, Docker Compose และ synthetic golden tests
- **v0.2 — OCR Quality:** PaddleOCR provider, mixed-page handling, image preprocessing, benchmark report และ manual correction UI
- **v0.3 — Agent Ready:** MCP server, TypeScript SDK publication, webhook completion callback และ richer OpenAI-compatible/Ollama configuration
- **v0.4 — More Documents:** orders, announcements, meeting minutes, invoices และ versioned custom extraction schemas
- **v0.5 — Production Storage:** PostgreSQL, S3-compatible artifacts, resumable jobs, metrics และ backup/restore documentation
- **v0.7 — Extensibility:** documented OCR/extractor/provider plugin interfaces, community schema registry และ evaluation CLI
- **v1.0 — Stable Release:** stable Python/API/schema contracts, migration policy, security review, reproducible benchmark, complete documentation และ upgrade guide

RAG/chat, workflow builder, multi-user/RBAC, hosted SaaS และ native mobile packaging อยู่นอกขอบเขต v1.0

## 6. First 20 GitHub Issues

1. **Initialize monorepo, uv workspace, linting and CI** — `type:chore`, `v0.1`
2. **Define Pydantic extraction and provenance models** — `type:feature`, `v0.1`
3. **Implement PDF/PNG/JPEG document loaders** — `type:feature`, `v0.1`
4. **Detect digital, scanned and mixed PDF pages** — `type:feature`, `v0.1`
5. **Add Tesseract tha+eng OCR provider** — `type:feature`, `v0.1`
6. **Build Thai Unicode and OCR-noise normalizer** — `type:feature`, `good first issue`
7. **Parse Thai digits and numeric expressions** — `type:feature`, `good first issue`
8. **Parse Buddhist Era and Thai date formats** — `type:feature`, `v0.1`
9. **Reconstruct page blocks and field provenance** — `type:feature`, `v0.1`
10. **Define versioned ThaiOfficialLetter schema** — `type:feature`, `documentation`
11. **Implement rule-based official-letter extractor** — `type:feature`, `v0.1`
12. **Add confidence scoring and validation warnings** — `type:feature`, `v0.1`
13. **Implement optional OpenAI-compatible/Ollama provider** — `type:feature`, `v0.1`
14. **Create thaidoc extract CLI and JSON output** — `type:feature`, `good first issue`
15. **Implement FastAPI v1 extraction and capability endpoints** — `type:feature`, `api`
16. **Add SQLite models, Alembic migrations and 24-hour cleanup** — `type:feature`, `database`
17. **Add Redis/arq async processing and job progress** — `type:feature`, `worker`
18. **Build Ionic Angular upload and result-review screens** — `type:feature`, `frontend`
19. **Create synthetic fixtures, golden tests and benchmark command** — `type:test`, `dataset`
20. **Publish bilingual README, contributor docs and logo assets** — `type:docs`, `good first issue`

แต่ละ issue ต้องมี motivation, bounded acceptance criteria, test expectation, dependencies และตัวอย่าง input/output; issue 6, 7, 14 และส่วนย่อยของ 20 ใช้เป็น contributor onboarding

## 7. Test and Acceptance Plan

- Unit tests ครอบคลุมเลขไทย, พ.ศ./ค.ศ., Unicode, OCR noise และ schema validation
- Golden tests ใช้เอกสาร synthetic สำหรับ external letter, internal memo, missing fields, หลายผู้ลงนาม และหลายหน้า
- Integration tests ครอบคลุม digital PDF, scanned PDF, mixed PDF, corrupt/encrypted file และ unsupported MIME
- Contract tests ตรวจ OpenAPI, sync `200`, async `202`, job lifecycle, error format และ idempotency
- Provider tests ใช้ mocked OpenAI-compatible/Ollama responses; default suite ห้ามต้องใช้ network/API key
- Retention tests ตรวจการลบ metadata และ artifacts หลัง TTL
- Web E2E ตรวจ upload, progress, result, provenance และ download JSON
- Acceptance gate ของ v0.1: `docker compose up --build` แล้วผู้ใช้สามารถอัปโหลด sample PDF และได้ valid JSON โดยไม่ตั้ง AI key
- CI บังคับ lint, type-check, unit/integration tests, dependency audit, container build และ generated OpenAPI diff

## Assumptions and Defaults

- Repository, PyPI `thaidoc` และ npm `@thaidoc/sdk` ดูว่าง ณ วันที่วางแผน แต่ต้องตรวจซ้ำก่อน publish
- Documentation ใช้ English-first พร้อม Thai quick start เพื่อรองรับทั้งผู้ใช้ไทยและ contributor ต่างประเทศ
- Web เป็น responsive PWA; ยังไม่เพิ่ม Capacitor/native builds
- SQLite + local storage เป็นค่าตั้งต้น ส่วน PostgreSQL/S3 ต้องใช้ adapter เดียวกันโดยไม่เปลี่ยน public API
- Schema และ REST API ใช้ semantic versioning; breaking changes ทำได้ใน `0.x` แต่ต้องมี changelog และ migration note
