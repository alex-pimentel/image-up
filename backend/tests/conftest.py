"""Shared pytest fixtures.

The integration suite runs without a real Redis or Celery broker: the task
store is backed by an in-process fake Redis and the Celery task's
``apply_async`` is mocked so the API contract can be exercised end-to-end.
"""

from __future__ import annotations

import dataclasses
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture()
def fake_redis(monkeypatch):
    """Patch ``redis.Redis.from_url`` with a fresh FakeRedis instance."""
    import fakeredis
    import redis

    server = fakeredis.FakeServer()

    def _from_url(*_args, **_kwargs):
        return fakeredis.FakeRedis(server=server, decode_responses=True)

    monkeypatch.setattr(redis.Redis, "from_url", staticmethod(_from_url))
    return server


def patch_settings(monkeypatch, module, **changes):
    """Replace a module's frozen ``settings`` singleton with modified values."""
    monkeypatch.setattr(
        module, "settings", dataclasses.replace(module.settings, **changes)
    )


class EnqueuedClient(TestClient):
    """TestClient that records Celery ``apply_async`` kwargs."""

    enqueued: list[dict]


@pytest.fixture()
def api_client(fake_redis, monkeypatch, tmp_path):
    """A TestClient with isolated storage + a mocked Celery enqueue."""
    from app import config, task_store, worker
    from app import main as main_module
    from app.services import upscaler

    uploads = tmp_path / "uploads"
    results = tmp_path / "results"
    uploads.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)

    new_settings = dataclasses.replace(
        config.settings, uploads_dir=uploads, results_dir=results
    )
    for module in (main_module, worker, upscaler, task_store, config):
        monkeypatch.setattr(module, "settings", new_settings)

    captured: list[dict] = []

    def _apply_async(*_args, **kwargs):
        captured.append(kwargs)
        return None

    monkeypatch.setattr(main_module.enhance_task, "apply_async", _apply_async)

    # Fresh in-process store bound to the fake Redis instance.
    monkeypatch.setattr(main_module, "store", task_store.TaskStore())

    with EnqueuedClient(main_module.app) as client:
        client.enqueued = captured
        yield client


def make_png_bytes(width: int = 8, height: int = 8, color: str = "red") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()
