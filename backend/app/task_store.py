"""Redis-backed task store, namespaced under REDIS_KEY_PREFIX so multiple
projects sharing the same Redis instance never collide.

Layout:
    imageup:task:{id}        -> hash of task fields
    imageup:task:{id}:lock  -> short-lived lock during processing (optional)
"""
from __future__ import annotations

import logging
from typing import Optional

from redis import Redis

from .config import settings
from .schemas import TaskStatus

logger = logging.getLogger(__name__)


class TaskStore:
    def __init__(self, redis_url: Optional[str] = None, prefix: Optional[str] = None) -> None:
        self.redis = Redis.from_url(redis_url or settings.redis_url, decode_responses=True)
        self.prefix = (prefix or settings.redis_key_prefix).rstrip(":") + ":"
        self.ttl = settings.result_ttl_sec

    def _key(self, task_id: str) -> str:
        return f"{self.prefix}task:{task_id}"

    def create(
        self,
        task_id: str,
        original_filename: str,
        original_path: str,
        original_url: Optional[str] = None,
        status: TaskStatus = TaskStatus.PENDING,
    ) -> None:
        import time

        data = {
            "task_id": task_id,
            "status": status.value,
            "original_filename": original_filename,
            "original_path": original_path,
            "original_url": original_url or "",
            "result_path": "",
            "result_url": "",
            "detail": "",
            "started_at": str(time.time()),
            "finished_at": "",
        }
        self.redis.hset(self._key(task_id), mapping=data)  # type: ignore[arg-type]
        self.redis.expire(self._key(task_id), self.ttl)

    def get(self, task_id: str) -> Optional[dict]:
        raw = self.redis.hgetall(self._key(task_id))
        if not raw:
            return None
        return raw

    def update(self, task_id: str, **changes) -> None:
        if not changes:
            return
        mapping: dict = {}
        for k, v in changes.items():
            mapping[k] = "" if v is None else str(v)
        self.redis.hset(self._key(task_id), mapping=mapping)
        if TaskStatus(changes.get("status", "")) in (TaskStatus.DONE, TaskStatus.ERROR):
            import time

            self.redis.hset(self._key(task_id), "finished_at", str(time.time()))

    def delete(self, task_id: str) -> None:
        self.redis.delete(self._key(task_id))


def status_from_raw(raw: dict) -> TaskStatus:
    try:
        return TaskStatus(raw.get("status", TaskStatus.PENDING))
    except ValueError:
        return TaskStatus.PENDING


def elapsed_from_raw(raw: dict) -> Optional[float]:
    try:
        started = float(raw.get("started_at") or 0)
        finished = float(raw.get("finished_at") or 0)
        if not started:
            return None
        end = finished if finished else __import__("time").time()
        return round(end - started, 2)
    except (TypeError, ValueError):
        return None


def detail_or_none(raw: dict) -> Optional[str]:
    d = raw.get("detail") or ""
    return d or None


def result_or_none(raw: dict) -> Optional[str]:
    v = raw.get("result_url") or ""
    return v or None


def mapping_for_backend(task_id: str) -> dict:
    """Read a task row to relay to the worker (paths)."""
    raw = TaskStore().get(task_id)
    return raw or {}