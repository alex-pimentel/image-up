"""Pydantic schemas for API request/response bodies."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class TaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class EnhanceResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    original_filename: str | None = None
    original_url: str | None = None
    result_url: str | None = None
    elapsed_sec: float | None = None
    detail: str | None = None
    backend: str | None = None  # "ml" / "fallback"


class LimitsResponse(BaseModel):
    max_upload_mb: int
    max_input_px: int
    allowed_extensions: list[str]
    output_quality: int
    output_format: str


class HealthResponse(BaseModel):
    status: str
    version: str
    ml_available: bool
    backend: str  # "ml" or "fallback"
    model_name: str | None = None
