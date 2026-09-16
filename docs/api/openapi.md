# REST API v1

The running service exposes authoritative OpenAPI documentation at `/docs` and `/openapi.json`.

## Create an extraction

`POST /v1/extractions` accepts multipart fields `file`, `schema`, `mode`, and `execution`. `Idempotency-Key` is optional. The only v0.1 schema is `thai_official_letter`.

- `execution=auto`: synchronous at or below five pages and 10 MiB, otherwise asynchronous.
- `execution=sync`: returns the extraction as `200`; exceeding the threshold returns `422 sync_limit_exceeded`.
- `execution=async`: returns a `202` job.

## Jobs

- `GET /v1/jobs/{id}` returns lifecycle state and progress.
- `GET /v1/jobs/{id}/result` returns a completed result or `409`.
- `DELETE /v1/jobs/{id}` permanently deletes the job, result, and artifacts.

## Discovery and health

- `GET /v1/schemas`
- `GET /v1/capabilities`
- `GET /health/live`
- `GET /health/ready`

Errors use `application/problem+json` with `type`, `title`, `status`, `code`, `detail`, `request_id`, and `errors`.

