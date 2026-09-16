from __future__ import annotations

import shutil
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any, cast
from uuid import uuid4

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.responses import Response
from thaidoc import __version__

from thaidoc_api.db import (
    ExtractionJobRecord,
    ExtractionResultRecord,
    create_schema,
    session_scope,
)
from thaidoc_api.schemas import JobResponse, ProblemDetail
from thaidoc_api.service import create_job, inspect_upload, process_job
from thaidoc_api.settings import settings


def _problem(request: Request, status: int, code: str, title: str, detail: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    payload = ProblemDetail(
        type=f"https://thaidoc.dev/problems/{code}",
        title=title,
        status=status,
        code=code,
        detail=detail,
        request_id=request_id,
    )
    return JSONResponse(payload.model_dump(), status_code=status, media_type="application/problem+json")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    create_schema()
    yield


app = FastAPI(
    title="Thai Document Intelligence API",
    version=__version__,
    description="Extract structured, verifiable data from Thai documents.",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    response = _problem(request, 422, "validation_error", "Invalid request", "Request validation failed")
    payload = cast(bytes, response.body).decode("utf-8")
    import json

    data = json.loads(payload)
    data["errors"] = [
        {"field": ".".join(str(item) for item in error["loc"]), "message": error["msg"]} for error in exc.errors()
    ]
    return JSONResponse(data, status_code=422, media_type="application/problem+json")


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException) -> JSONResponse:
    code = {
        401: "unauthorized",
        404: "not_found",
        409: "job_not_ready",
        503: "service_unavailable",
    }.get(exc.status_code, "request_failed")
    return _problem(request, exc.status_code, code, "Request failed", str(exc.detail))


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Missing or invalid API key")


def _mime_type(content: bytes) -> str:
    if content.startswith(b"%PDF"):
        return "application/pdf"
    if content.startswith(b"\x89PNG"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return "application/octet-stream"


@app.post("/v1/extractions", dependencies=[Depends(require_api_key)], response_model=None)
async def create_extraction(
    request: Request,
    file: Annotated[UploadFile, File()],
    schema_name: Annotated[str, Form(alias="schema")] = "thai_official_letter",
    mode: Annotated[str, Form(pattern="^(rules|ai|auto)$")] = "auto",
    execution: Annotated[str, Form(pattern="^(auto|sync|async)$")] = "auto",
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any] | JSONResponse:
    if schema_name != "thai_official_letter":
        return _problem(request, 422, "unsupported_schema", "Unsupported schema", schema_name)
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        return _problem(request, 413, "file_too_large", "File too large", "Maximum size is 50 MiB")
    mime_type = _mime_type(content)
    try:
        page_count = inspect_upload(content, mime_type)
    except ValueError as exc:
        return _problem(request, 422, "invalid_document", "Invalid document", str(exc))
    if page_count > settings.max_pages:
        return _problem(request, 413, "too_many_pages", "Too many pages", "Maximum is 200 pages")

    requires_async = len(content) > settings.sync_max_bytes or page_count > settings.sync_max_pages
    if execution == "sync" and requires_async:
        return _problem(
            request,
            422,
            "sync_limit_exceeded",
            "Synchronous limit exceeded",
            "Use execution=async for this document",
        )
    resolved_execution = "async" if execution == "async" or (execution == "auto" and requires_async) else "sync"
    job, created = create_job(
        content=content,
        filename=file.filename or "document",
        mime_type=mime_type,
        page_count=page_count,
        schema_name=schema_name,
        mode=mode,
        execution=resolved_execution,
        idempotency_key=idempotency_key,
    )
    if not created:
        return JSONResponse(JobResponse.model_validate(job).model_dump(mode="json"), status_code=200)
    if resolved_execution == "sync":
        try:
            return process_job(job.id)
        except Exception as exc:
            return _problem(request, 422, "extraction_failed", "Extraction failed", str(exc))

    try:
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await redis.enqueue_job("extract_document", job.id)
        await redis.close()
    except Exception:
        return _problem(request, 503, "queue_unavailable", "Queue unavailable", "Redis is unavailable")
    return JSONResponse(JobResponse.model_validate(job).model_dump(mode="json"), status_code=202)


@app.get("/v1/jobs/{job_id}", response_model=JobResponse, dependencies=[Depends(require_api_key)])
def get_job(job_id: str) -> ExtractionJobRecord:
    with session_scope() as session:
        job = session.get(ExtractionJobRecord, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        session.expunge(job)
        return job


@app.get("/v1/jobs/{job_id}/result", dependencies=[Depends(require_api_key)])
def get_job_result(job_id: str) -> dict[str, Any]:
    with session_scope() as session:
        job = session.get(ExtractionJobRecord, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status != "succeeded":
            raise HTTPException(status_code=409, detail=f"Job is {job.status}")
        result = session.scalar(select(ExtractionResultRecord).where(ExtractionResultRecord.job_id == job_id))
        assert result is not None
        return result.result_json


@app.delete("/v1/jobs/{job_id}", status_code=204, dependencies=[Depends(require_api_key)])
def delete_job(job_id: str) -> None:
    with session_scope() as session:
        job = session.get(ExtractionJobRecord, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        document = job.document
        session.delete(document)
    shutil.rmtree(settings.artifact_dir / job_id, ignore_errors=True)


@app.get("/v1/schemas")
def list_schemas() -> list[dict[str, str]]:
    return [{"name": "thai_official_letter", "version": "1.0.0"}]


@app.get("/v1/capabilities")
def capabilities() -> dict[str, Any]:
    return {
        "formats": ["application/pdf", "image/png", "image/jpeg"],
        "ocr": ["tesseract"],
        "ai_providers": ["openai-compatible"] if settings.ai_base_url and settings.ai_model else [],
        "limits": {"max_bytes": settings.max_upload_bytes, "max_pages": settings.max_pages},
    }


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    try:
        with session_scope() as session:
            session.execute(select(1))
        return {"status": "ready"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
