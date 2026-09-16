from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    id: str
    status: Literal["queued", "processing", "succeeded", "failed", "expired"]
    progress: int = Field(ge=0, le=100)
    schema_name: str
    execution: str
    created_at: datetime
    updated_at: datetime
    error_code: str | None = None
    error_detail: str | None = None

    model_config = {"from_attributes": True}


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    code: str
    detail: str
    request_id: str
    errors: list[dict[str, str]] = Field(default_factory=list)
