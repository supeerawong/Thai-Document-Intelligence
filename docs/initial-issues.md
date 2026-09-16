# Initial GitHub issues

Each issue below is intentionally bounded. Copy the section into GitHub and apply the listed labels and milestone.

## 1. Initialize monorepo, uv workspace, linting and CI

**Labels:** `type:chore` · **Milestone:** `v0.1` · **Dependencies:** none

**Motivation:** Contributors need one reproducible setup.  
**Acceptance:** `uv sync --all-extras`, `pytest`, `ruff check .`, mypy, and both TypeScript builds run in CI; dependency cache is enabled.  
**Tests:** CI passes from a clean checkout.  
**Example:** `uv run thaidoc --help` exits successfully.

## 2. Define Pydantic extraction and provenance models

**Labels:** `type:feature` · **Milestone:** `v0.1` · **Dependencies:** #1

**Motivation:** Every adapter needs one typed result contract.  
**Acceptance:** Public models validate confidence bounds, page numbers, methods, and generic results.  
**Tests:** Valid round-trip and invalid boundary cases.  
**Example:** a provenance page of `0` is rejected.

## 3. Implement PDF/PNG/JPEG document loaders

**Labels:** `type:feature` · **Milestone:** `v0.1` · **Dependencies:** #2

**Motivation:** Core extraction must accept common document sources.  
**Acceptance:** bytes and paths work; file signatures win over extensions; unsupported/encrypted/corrupt inputs have safe errors.  
**Tests:** one fixture per supported and failure type.  
**Example:** a renamed PNG is still detected as PNG.

## 4. Detect digital, scanned and mixed PDF pages

**Labels:** `type:feature` · **Milestone:** `v0.1` · **Dependencies:** #3

**Motivation:** OCR should run only where embedded text is unusable.  
**Acceptance:** classification is per page and the selected method is recorded.  
**Tests:** digital, scanned, and two-page mixed fixtures.  
**Example:** page 1=`digital_text`, page 2=`ocr`.

## 5. Add Tesseract tha+eng OCR provider

**Labels:** `type:feature` · **Milestone:** `v0.1` · **Dependencies:** #3

**Motivation:** The default path must remain local.  
**Acceptance:** provider protocol and Tesseract implementation support configurable language and clear missing-binary errors.  
**Tests:** mocked OCR plus one optional Docker integration fixture.  
**Example:** `recognize(image, language="tha+eng")` returns text.

## 6. Build Thai Unicode and OCR-noise normalizer

**Labels:** `type:feature`, `good first issue` · **Milestone:** `v0.1` · **Dependencies:** #1

**Motivation:** Invisible marks and whitespace break field rules.  
**Acceptance:** NFC, zero-width removal, Thai-digit conversion, and whitespace normalization are deterministic.  
**Tests:** parameterized Thai examples.  
**Example:** `๒๕๖๙` becomes `2569`.

## 7. Parse Thai digits and numeric expressions

**Labels:** `type:feature`, `good first issue` · **Milestone:** `v0.1` · **Dependencies:** #6

**Motivation:** Official identifiers mix Thai and Arabic digits.  
**Acceptance:** digit conversion preserves punctuation and surrounding Thai text.  
**Tests:** integers, decimals, slashes, and mixed text.  
**Example:** `ที่ ๑๒/๒๕๖๙` becomes `ที่ 12/2569`.

## 8. Parse Buddhist Era and Thai date formats

**Labels:** `type:feature` · **Milestone:** `v0.1` · **Dependencies:** #6

**Motivation:** Dates need safe ISO normalization without losing their source.  
**Acceptance:** full and abbreviated Thai months work; invalid dates retain original and return `iso=null`.  
**Tests:** Buddhist, Gregorian, invalid leap day, and unknown month.  
**Example:** `16 กันยายน 2569` → `2026-09-16`.

## 9. Reconstruct page blocks and field provenance

**Labels:** `type:feature` · **Milestone:** `v0.1` · **Dependencies:** #3, #4

**Motivation:** Users must inspect where a value came from.  
**Acceptance:** page, method, source text, and bounding box when available follow every extracted field.  
**Tests:** provenance points to the expected page/block.  
**Example:** subject evidence references page 1.

## 10. Define versioned ThaiOfficialLetter schema

**Labels:** `type:feature`, `documentation` · **Milestone:** `v0.1` · **Dependencies:** #2

**Motivation:** Consumers need a stable domain contract.  
**Acceptance:** all planned fields, enums, null behavior, JSON example, and versioning policy are documented.  
**Tests:** complete and sparse payload validation.  
**Example:** missing recipient is `null`, not an invented string.

## 11. Implement rule-based official-letter extractor

**Labels:** `type:feature` · **Milestone:** `v0.1` · **Dependencies:** #8–#10

**Motivation:** Core value must work without AI.  
**Acceptance:** identify document type and extract header, body, signer, and contact fields from synthetic documents.  
**Tests:** golden fixtures for five document variations.  
**Example:** `เรื่อง ขอเชิญประชุม` extracts the subject.

## 12. Add confidence scoring and validation warnings

**Labels:** `type:feature` · **Milestone:** `v0.1` · **Dependencies:** #11

**Motivation:** Downstream systems need uncertainty, not silent guesses.  
**Acceptance:** scores stay in `[0,1]`; missing/invalid fields add warnings without failing the document.  
**Tests:** sparse and ambiguous fixtures.  
**Example:** no date adds `Could not extract date`.

## 13. Implement optional OpenAI-compatible/Ollama provider

**Labels:** `type:feature` · **Milestone:** `v0.1` · **Dependencies:** #10, #12

**Motivation:** Low-confidence fields may benefit from a configured model.  
**Acceptance:** vendor-neutral base URL/model settings, structured validation, timeouts, redacted errors, and no default network call.  
**Tests:** mocked success, invalid JSON, timeout, and provider-disabled cases.  
**Example:** `mode=ai` without a provider fails clearly.

## 14. Create thaidoc extract CLI and JSON output

**Labels:** `type:feature`, `good first issue` · **Milestone:** `v0.1` · **Dependencies:** #11

**Motivation:** The library needs a scriptable local interface.  
**Acceptance:** schema, mode, output path, stdout, exit codes, and Unicode JSON work.  
**Tests:** Typer runner tests for stdout/output/error.  
**Example:** `thaidoc extract sample.pdf -o result.json`.

## 15. Implement FastAPI v1 extraction and capability endpoints

**Labels:** `type:feature`, `api` · **Milestone:** `v0.1` · **Dependencies:** #11, #12

**Motivation:** Other applications require a stable HTTP adapter.  
**Acceptance:** planned routes, thresholds, signature validation, request IDs, and problem JSON are in OpenAPI.  
**Tests:** contract tests for 200/202/4xx and discovery.  
**Example:** a 6-page forced-sync request gets `sync_limit_exceeded`.

## 16. Add SQLite models, migrations and 24-hour cleanup

**Labels:** `type:feature`, `database` · **Milestone:** `v0.1` · **Dependencies:** #15

**Motivation:** Async jobs need durable state and governed retention.  
**Acceptance:** all planned tables, Alembic initial migration, cascade deletion, TTL setting, and artifact cleanup exist.  
**Tests:** migration upgrade and expired/non-expired cleanup.  
**Example:** a job beyond TTL loses both row and source file.

## 17. Add Redis/arq async processing and job progress

**Labels:** `type:feature`, `worker` · **Milestone:** `v0.1` · **Dependencies:** #15, #16

**Motivation:** Large OCR jobs must not hold an HTTP request.  
**Acceptance:** queued jobs reach terminal state, failures are sanitized, and retries do not duplicate results.  
**Tests:** worker integration with Redis and failure simulation.  
**Example:** `execution=async` returns `202` and a job ID.

## 18. Build Ionic Angular upload and result-review screens

**Labels:** `type:feature`, `frontend` · **Milestone:** `v0.1` · **Dependencies:** #15, #17

**Motivation:** A visual demo lets non-Python users evaluate extraction.  
**Acceptance:** responsive upload, progress, problem display, JSON/provenance review, and download work with keyboard navigation.  
**Tests:** component tests and one browser happy path.  
**Example:** upload a PDF and download `thaidoc-result.json`.

## 19. Create synthetic fixtures, golden tests and benchmark command

**Labels:** `type:test`, `dataset` · **Milestone:** `v0.1` · **Dependencies:** #11

**Motivation:** Quality needs reproducible evidence without private documents.  
**Acceptance:** five fixture families, expected JSON, field precision/recall command, fixture license, and deterministic CI subset.  
**Tests:** benchmark detects an intentionally changed expected field.  
**Example:** report per-field and macro F1.

## 20. Publish bilingual README, contributor docs and logo assets

**Labels:** `type:docs`, `good first issue` · **Milestone:** `v0.1` · **Dependencies:** #14, #15, #18

**Motivation:** Users and first-time contributors need a credible landing page.  
**Acceptance:** English-first README with Thai quick start, SVG/PNG assets, architecture, privacy, warning, contribution and security docs.  
**Tests:** links and quick-start commands are checked in CI.  
**Example:** a new contributor can run one sample without an AI key.

