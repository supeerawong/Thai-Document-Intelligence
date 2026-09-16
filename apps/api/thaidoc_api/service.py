from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pymupdf
from sqlalchemy import select
from thaidoc import extract
from thaidoc.ocr import ImagePreprocessingOptions, create_ocr_provider
from thaidoc.providers import OpenAICompatibleProvider
from thaidoc.schemas import ThaiOfficialLetter

from thaidoc_api.db import (
    ArtifactRecord,
    DocumentRecord,
    ExtractionJobRecord,
    ExtractionResultRecord,
    session_scope,
)
from thaidoc_api.settings import settings


def inspect_upload(content: bytes, mime_type: str) -> int:
    if mime_type == "application/pdf":
        try:
            with pymupdf.open(  # type: ignore[no-untyped-call]
                stream=content, filetype="pdf"
            ) as document:
                if document.needs_pass:
                    raise ValueError("Encrypted PDF files are not supported")
                return int(document.page_count)
        except pymupdf.FileDataError as exc:
            raise ValueError("The uploaded PDF is corrupt or invalid") from exc
    if mime_type in {"image/png", "image/jpeg"}:
        return 1
    raise ValueError(f"Unsupported document type: {mime_type}")


def create_job(
    *,
    content: bytes,
    filename: str,
    mime_type: str,
    page_count: int,
    schema_name: str,
    mode: str,
    execution: str,
    idempotency_key: str | None,
) -> tuple[ExtractionJobRecord, bool]:
    expires_at = datetime.now(UTC) + timedelta(hours=settings.retention_hours)
    checksum = hashlib.sha256(content).hexdigest()
    with session_scope() as session:
        if idempotency_key:
            existing = session.scalar(
                select(ExtractionJobRecord).where(
                    ExtractionJobRecord.idempotency_key == idempotency_key,
                    ExtractionJobRecord.schema_name == schema_name,
                    ExtractionJobRecord.mode == mode,
                )
            )
            if existing:
                session.expunge(existing)
                return existing, False
        document = DocumentRecord(
            sha256=checksum,
            filename=filename,
            mime_type=mime_type,
            size=len(content),
            page_count=page_count,
            expires_at=expires_at,
        )
        job = ExtractionJobRecord(
            document=document,
            schema_name=schema_name,
            mode=mode,
            execution=execution,
            idempotency_key=idempotency_key,
        )
        session.add(job)
        session.flush()
        job_dir = settings.artifact_dir / job.id
        job_dir.mkdir(parents=True, exist_ok=True)
        path = job_dir / "source"
        path.write_bytes(content)
        session.add(
            ArtifactRecord(
                job=job,
                kind="source",
                storage_key=str(path),
                checksum=checksum,
                size=len(content),
                expires_at=expires_at,
            )
        )
        session.flush()
        session.expunge(job)
        return job, True


def process_job(job_id: str) -> dict[str, Any]:
    with session_scope() as session:
        job = session.get(ExtractionJobRecord, job_id)
        if not job:
            raise ValueError("Job not found")
        job.status = "processing"
        job.progress = 10
        artifact = session.scalar(
            select(ArtifactRecord).where(ArtifactRecord.job_id == job_id, ArtifactRecord.kind == "source")
        )
        if not artifact:
            raise ValueError("Source artifact not found")
        source_path = artifact.storage_key
        mode = job.mode

    try:
        provider = None
        if settings.ai_base_url and settings.ai_model:
            provider = OpenAICompatibleProvider(
                base_url=settings.ai_base_url,
                model=settings.ai_model,
                api_key=settings.ai_api_key,
                timeout=settings.ai_timeout_seconds,
            )
        result = extract(
            Path(source_path),
            schema=ThaiOfficialLetter,
            mode=mode,
            provider=provider,
            ocr=create_ocr_provider(settings.ocr_provider),
            preprocessing=ImagePreprocessingOptions(enabled=settings.ocr_preprocess),
        )
        payload = result.model_dump(mode="json")
        with session_scope() as session:
            job = session.get(ExtractionJobRecord, job_id)
            assert job is not None
            job.status = "succeeded"
            job.progress = 100
            session.add(
                ExtractionResultRecord(
                    job=job,
                    schema_version=result.schema_version,
                    result_json=payload,
                    confidence=result.document.confidence,
                    warnings=result.warnings,
                )
            )
        return payload
    except Exception as exc:
        with session_scope() as session:
            job = session.get(ExtractionJobRecord, job_id)
            if job:
                job.status = "failed"
                job.error_code = "extraction_failed"
                job.error_detail = str(exc)[:500]
        raise
