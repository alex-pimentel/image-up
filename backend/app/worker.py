"""Celery application + worker task.

One worker process consumes jobs from the broker; the FastAPI web process
only enqueues them. The result cache and per-task metadata live under the
imageup:* Redis keyspace, and the CELERY_RESULT_BACKEND (which writes to its
own redis keyspace) is also namespaced via Celery's `result_path/tests` to
avoid collisions.

Run the worker with:
    celery -A app.worker worker --loglevel=info --concurrency=1
"""
from __future__ import annotations

import logging
from pathlib import Path

from celery import Celery

from .config import settings
from .schemas import TaskStatus
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
    # Namespacing for Celery's internal keys (results, etc.)
    result_backend_transport_options={"global_keyprefix": settings.redis_key_prefix.replace(":", "")},
    redis_backend_use_redis_group=False,
)


@celery_app.task(name="imageup.enhance", bind=True)
def enhance_task(self, task_id: str, input_path: str, original_filename: str, scale: int = 4) -> dict:
    store = TaskStore()
    store.update(task_id, status=TaskStatus.PROCESSING.value)

    ext = settings.output_extension
    out_name = Path(input_path).stem + f"_x{scale}.{ext}"
    output_path = settings.results_dir / out_name

    backend = backend_label()
    try:
        upscale(Path(input_path), output_path, scale=scale)
        result_url = f"/api/results/{out_name}"
        store.update(
            task_id,
            status=TaskStatus.DONE.value,
            result_path=str(output_path),
            result_url=result_url,
            detail=backend,
        )
        return {"task_id": task_id, "status": "done", "result_url": result_url, "backend": backend}
    except Exception as e:  # pragma: no cover - error path
        logger.exception("enhance_task failed for %s: %s", task_id, e)
        store.update(task_id, status=TaskStatus.ERROR.value, detail=str(e))
        return {"task_id": task_id, "status": "error", "detail": str(e)}