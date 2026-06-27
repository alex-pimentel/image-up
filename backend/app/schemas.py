"""Pydantic schemas for API request/response bodies."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TaskStatus(str, Enum):
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
    original_filename: Optional[str] = None
    original_url: Optional[str] = None
    result_url: Optional[str] = None
    elapsed_sec: Optional[float] = None
    detail: Optional[str] = None
    backend: Optional[str] = None  # "ml" / "fallback"


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
    model_name: Optional[str] = None