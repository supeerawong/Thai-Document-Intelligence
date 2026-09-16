# Architecture

The Python package owns all document-processing behavior. HTTP, worker, web, and SDK layers are adapters and must not contain extraction rules.

## Pipeline

1. The loader validates file signatures and reads PDF pages or images.
2. PDF pages with usable embedded text use `digital_text`; sparse pages are rendered and sent to the configured `OCRProvider`.
3. Thai text normalization applies Unicode NFC, removes zero-width markers, converts Thai digits, and normalizes whitespace.
4. The schema extractor classifies the document and applies deterministic field rules.
5. When `mode=auto`, a configured `StructuredExtractionProvider` may handle a result below the confidence threshold.
6. Pydantic validates the schema. The result contains warnings and field-level provenance.

## Boundaries

- `thaidoc`: deterministic core, provider protocols, public models, CLI.
- `thaidoc_api`: validation, persistence, job lifecycle, and HTTP contracts.
- `thaidoc_worker`: queued extraction and retention cleanup.
- `apps/web`: an API client only; it does not reproduce extraction logic.
- `@thaidoc/sdk`: generated-compatible typed transport client.

SQLite and local storage are default adapters. Database records store artifact keys rather than file bytes, allowing PostgreSQL and S3-compatible adapters without changing public responses.

## Trust and privacy

Input is untrusted. File signatures are checked before parsing, upload/page limits are enforced, and errors are sanitized. AI is opt-in and must never receive a document unless the deployer configured a provider. No telemetry is emitted.

