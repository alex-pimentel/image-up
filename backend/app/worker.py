"""Celery application + worker task.

One worker process consumes jobs from the broker; the FastAPI web process
only enqueues them. The result cache and per-task metadata live under the
imageup:* Redis keyspace, and the CELERY_RESULT_BACKEND (which writes to its
own redis keyspace) is also namespaced via Celery's `result_path/tests` to
avoid collisions.

Uploads and results live in Cloudflare R2 (private ``tmp`` bucket, 24h
lifecycle). The worker downloads the original from R2, upscales it to a
temporary file, and uploads the enhanced result back to R2.

Run the worker with:
    celery -A app.worker worker --loglevel=info --concurrency=1
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from celery import Celery
from kombu import Queue

from .config import settings
from .schemas import TaskStatus
from .services.storage import get_storage
from .services.upscaler import backend_label, upscale
from .task_store import TaskStore

logger = logging.getLogger(__name__)

celery_app = Celery(
    "imageup",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker"],
)

# Namespace Celery's own result keys so multiple projects on the same Redis
# don't collide.
celery_app.conf.update(
    result_expires=settings.result_ttl_sec,
    redis_backend_health_check_interval=30,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue=settings.celery_queue,
    task_queues=(Queue(settings.celery_queue),),
    task_create_missing_queues=False,
    # Namespacing for Celery's internal keys (results, etc.)
    result_backend_transport_options={"global_keyprefix": settings.redis_key_prefix.replace(":", "")},
    redis_backend_use_redis_group=False,
)


@celery_app.task(name="imageup.enhance", bind=True)
def enhance_task(self, task_id: str, upload_key: str, original_filename: str, scale: int = 2) -> dict:
    store = TaskStore()
    store.update(task_id, status=TaskStatus.PROCESSING.value)

    ext = settings.output_extension
    suffix = Path(original_filename).suffix.lower() or ".png"
    backend = backend_label()
    try:
        storage = get_storage()
        with tempfile.TemporaryDirectory(prefix="imageup-") as tmp:
            in_path = Path(tmp) / f"input{suffix}"
            out_path = Path(tmp) / f"result.{ext}"
            storage.fetch_upload(upload_key, in_path)
            upscale(in_path, out_path, scale=scale)
            stored_key = storage.save_result(task_id, out_path)

        result_url = f"/api/results/{task_id}.{ext}"
        store.update(
            task_id,
            status=TaskStatus.DONE.value,
            result_key=stored_key,
            result_url=result_url,
            detail=backend,
        )
        return {"task_id": task_id, "status": "done", "result_url": result_url, "backend": backend}
    except Exception as e:  # pragma: no cover - error path
        logger.exception("enhance_task failed for %s", task_id)
        store.update(task_id, status=TaskStatus.ERROR.value, detail=str(e))
        return {"task_id": task_id, "status": "error", "detail": str(e)}
