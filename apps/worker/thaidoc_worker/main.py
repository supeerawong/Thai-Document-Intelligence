from __future__ import annotations

import shutil
from datetime import UTC, datetime
from typing import Any

from arq.connections import RedisSettings
from arq.cron import cron
from sqlalchemy import select
from thaidoc_api.db import DocumentRecord, create_schema, session_scope
from thaidoc_api.service import process_job
from thaidoc_api.settings import settings


async def extract_document(_ctx: dict[str, Any], job_id: str) -> dict[str, Any]:
    return process_job(job_id)


async def cleanup_expired(_ctx: dict[str, Any]) -> int:
    now = datetime.now(UTC)
    removed: list[str] = []
    with session_scope() as session:
        documents = session.scalars(select(DocumentRecord).where(DocumentRecord.expires_at <= now)).all()
        for document in documents:
            removed.extend(job.id for job in document.jobs)
            session.delete(document)
    for job_id in removed:
        shutil.rmtree(settings.artifact_dir / job_id, ignore_errors=True)
    return len(removed)


async def startup(_ctx: dict[str, Any]) -> None:
    create_schema()


class WorkerSettings:
    functions = [extract_document, cleanup_expired]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    cron_jobs = [cron("thaidoc_worker.main.cleanup_expired", minute={0})]
