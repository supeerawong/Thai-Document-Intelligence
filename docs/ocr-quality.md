# OCR quality (v0.2)

Thai Document Intelligence keeps Tesseract as the zero-cloud default and adds PaddleOCR as an optional local provider. Both providers use the same conservative preprocessing and benchmark path.

## Providers

Tesseract remains part of the base installation:

```bash
thaidoc extract letter.pdf --ocr-provider tesseract
```

PaddleOCR is intentionally optional because its local runtime and models are substantially larger:

```bash
pip install "thaidoc[paddle]"
thaidoc extract letter.pdf --ocr-provider paddle
```

The Paddle models may be downloaded by PaddleOCR on first use. Once the models are present locally, document inference stays on the machine. Set `THAIDOC_OCR_PROVIDER=paddle` for the API and worker.

## Preprocessing and mixed pages

Before OCR, images are EXIF-oriented, upscaled when small, converted to grayscale, and contrast-normalized. Denoising and Otsu binarization are available through `ImagePreprocessingOptions` for callers that need stronger cleanup. Disable the default path with `--no-preprocess` or `THAIDOC_OCR_PREPROCESS=false` when benchmarking raw input.

PDF decisions are made per page:

- usable embedded text: keep the digital layer;
- little or no embedded text: render and OCR the page;
- short embedded text plus a large image: OCR and merge unique lines, marking the page as `hybrid`.

Every OCR or hybrid page records the provider name in `PageContent.ocr_provider`.

## Reproducible benchmark

Create a UTF-8 JSONL manifest. Paths are relative to the manifest:

```json
{"id":"synthetic-01","source":"images/synthetic-01.png","reference":"เรื่อง ขอทดสอบระบบ\nเรียน ผู้อำนวยการ"}
```

Run either provider and keep both Markdown and machine-readable output:

```bash
thaidoc benchmark benchmarks/manifest.jsonl \
  --ocr-provider tesseract \
  --output reports/tesseract.md \
  --json-output reports/tesseract.json
```

The report contains per-case and mean character error rate (CER), word error rate (WER), and elapsed time. Do not commit real correspondence, personal data, generated extraction results, downloaded models, or temporary renders. Benchmark fixtures must be synthetic or openly licensed.

## Manual correction

After extraction, the web result card exposes **Correct**. It opens the complete result as editable JSON, validates the correction locally, and makes the corrected value available for download. This first correction workflow does not overwrite the stored extraction or send edits to an external service.
