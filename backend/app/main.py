"""FastAPI entry point."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import settings
from .schemas import (
    EnhanceResponse,
    HealthResponse,
    LimitsResponse,
    TaskStatus,
    TaskStatusResponse,
)
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

# Static results served from disk (enhanced + uploaded originals stored in same dir)
app.mount("/api/results", StaticFiles(directory=str(settings.results_dir)), name="results")

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


def _validate_image(path: Path) -> None:
    from PIL import Image

    try:
        with Image.open(path) as im:
            largest = max(im.width, im.height)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid or unreadable image: {e}")
    if largest > settings.max_input_px:
        raise HTTPException(
            status_code=422,
            detail=f"Input image too large: {largest}px. Maximum largest side is {settings.max_input_px}px.",
        )


@app.post("/api/enhance", response_model=EnhanceResponse)
async def enhance(
    file: UploadFile = File(...),
    scale: int = settings.default_scale,
) -> JSONResponse:
    if scale not in (2, 4):
        raise HTTPException(status_code=422, detail="scale must be 2 or 4")
    if not _ext_ok(file.filename or ""):
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Allowed: {', '.join(settings.allowed_extensions)}")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.max_upload_mb}MB.")

    task_id = _short_id()
    in_name = f"{task_id}{Path(file.filename or 'image').suffix.lower()}"
    in_path = settings.uploads_dir / in_name
    in_path.write_bytes(data)

    # Validate dimensions before enqueueing
    _validate_image(in_path)

    (settings.results_dir / in_name).write_bytes(data)
    original_url = f"/api/results/{in_name}"

    store.create(
        task_id=task_id,
        original_filename=file.filename or "image",
        original_path=str(in_path),
        original_url=original_url,
        status=TaskStatus.PENDING,
    )

    # Enqueue the Celery worker task (non-blocking)
    enhance_task.apply_async(
        kwargs={
            "task_id": task_id,
            "input_path": str(in_path),
            "original_filename": file.filename or "image",
            "scale": scale,
        },
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
        original_url=raw.get("original_url") or None,
        result_url=result_or_none(raw),
        elapsed_sec=elapsed_from_raw(raw),
        detail=detail_or_none(raw),
        backend=raw.get("detail") or None,
    )


def _short_id() -> str:
    import uuid

    return uuid.uuid4().hex[:12]