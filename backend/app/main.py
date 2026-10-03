"""FastAPI entry point."""
from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .auth import optional_clerk_user
from .config import settings
from .schemas import (
    EnhanceResponse,
    HealthResponse,
    LimitsResponse,
    TaskStatus,
    TaskStatusResponse,
)
from .services.storage import get_storage
from .services.upscaler import backend_label, is_ml_available
from .task_store import (
    TaskStore,
    detail_or_none,
    elapsed_from_raw,
    result_or_none,
    status_from_raw,
)
from .worker import enhance_task

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ImageUp API", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

store = TaskStore()


def _ext_ok(filename: str) -> bool:
    return Path(filename).suffix.lower().lstrip(".") in settings.allowed_extensions


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        ml_available=is_ml_available(),
        backend=backend_label(),
        model_name=settings.model_name if is_ml_available() else None,
    )


@app.get("/api/config", response_model=LimitsResponse)
def config() -> LimitsResponse:
    return LimitsResponse(
        max_upload_mb=settings.max_upload_mb,
        max_input_px=settings.max_input_px,
        allowed_extensions=list(settings.allowed_extensions),
        output_quality=settings.output_quality,
        output_format=settings.output_format,
    )


def _validate_image(data: bytes) -> None:
    from PIL import Image

    try:
        with Image.open(BytesIO(data)) as im:
            largest = max(im.width, im.height)
    except Exception as e:  # noqa: BLE001 - any decode error becomes a 422
        raise HTTPException(status_code=422, detail=f"Invalid or unreadable image: {e}")
    if largest > settings.max_input_px:
        raise HTTPException(
            status_code=422,
            detail=f"Input image too large: {largest}px. Maximum largest side is {settings.max_input_px}px.",
        )


@app.post("/api/enhance", response_model=EnhanceResponse)
async def enhance(
    file: UploadFile = File(...),  # noqa: B008 - FastAPI requires the File() sentinel here
    scale: int = settings.default_scale,
    claims: dict[str, Any] | None = Depends(optional_clerk_user),  # noqa: B008
) -> JSONResponse:
    if scale not in (2, 4):
        raise HTTPException(status_code=422, detail="scale must be 2 or 4")
    if not _ext_ok(file.filename or ""):
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Allowed: {', '.join(settings.allowed_extensions)}")

    # Authenticated users get a more generous limit; anonymous stays strict.
    max_upload_mb = settings.auth_max_upload_mb if claims else settings.max_upload_mb

    data = await file.read()
    if len(data) > max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Max {max_upload_mb}MB.")

    _validate_image(data)

    task_id = _short_id()
    filename = Path(file.filename or "image").name
    storage = get_storage()
    key = storage.save_upload(task_id, filename, data)

    store.create(
        task_id=task_id,
        original_filename=file.filename or "image",
        upload_key=key,
        status=TaskStatus.PENDING,
    )

    # Enqueue the Celery worker task (non-blocking). Only the R2 key travels.
    enhance_task.apply_async(
        kwargs={
            "task_id": task_id,
            "upload_key": key,
            "original_filename": file.filename or "image",
            "scale": scale,
        },
        queue=settings.celery_queue,
    )

    return JSONResponse({"task_id": task_id, "status": TaskStatus.PENDING.value})


@app.get("/api/status/{task_id}", response_model=TaskStatusResponse)
def status(task_id: str) -> TaskStatusResponse:
    raw = store.get(task_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Task not found (may have expired).")
    return TaskStatusResponse(
        task_id=task_id,
        status=status_from_raw(raw),
        original_filename=raw.get("original_filename") or None,
        original_url=f"/api/uploads/{task_id}" if raw.get("upload_key") else None,
        result_url=result_or_none(raw),
        elapsed_sec=elapsed_from_raw(raw),
        detail=detail_or_none(raw),
        backend=raw.get("detail") or None,
    )


@app.get("/api/uploads/{task_id}")
def get_upload(task_id: str):
    """Serve the original upload: 302 to a short-lived presigned R2 URL (or the local file)."""
    raw = store.get(task_id)
    key = (raw or {}).get("upload_key") or ""
    if not key:
        raise HTTPException(status_code=404, detail="Upload not found (may have expired).")
    return get_storage().response_for(key)


@app.get("/api/results/{filename}")
def get_result(filename: str):
    """Serve an enhanced result: 302 to a short-lived presigned R2 URL (or the local file)."""
    task_id, _, _ext = filename.rpartition(".")
    raw = store.get(task_id) if task_id else None
    key = (raw or {}).get("result_key") or ""
    if not key:
        raise HTTPException(status_code=404, detail="Result not found (may have expired).")
    return get_storage().response_for(key)


def _short_id() -> str:
    import uuid

    return uuid.uuid4().hex[:12]
