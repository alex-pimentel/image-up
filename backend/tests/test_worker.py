"""Tests for the Celery worker task.

The storage backend is the local-disk adapter (R2 disabled) and the ML upscaler
is patched out so the task can be driven as a plain function while still
exercising task-store transitions (processing -> done/error).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import worker as worker_module
from app.schemas import TaskStatus
from app.services.storage import LocalStorageAdapter
from app.task_store import TaskStore
from tests.conftest import make_png_bytes


@pytest.fixture()
def store(fake_redis):
    # Use the same key prefix as the worker's internally-constructed TaskStore.
    return TaskStore(redis_url="redis://localhost:6379/0")


@pytest.fixture()
def storage(tmp_path: Path) -> LocalStorageAdapter:
    return LocalStorageAdapter(tmp_path / "storage")


def test_enhance_task_marks_done(monkeypatch, store, storage, tmp_path):
    key = storage.save_upload("job1", "input.png", make_png_bytes())

    def _fake_upscale(_in_path, out_path, scale=2):
        Path(out_path).write_bytes(b"upscaled")

    monkeypatch.setattr(worker_module, "get_storage", lambda: storage)
    monkeypatch.setattr(worker_module, "upscale", _fake_upscale)
    monkeypatch.setattr(worker_module, "backend_label", lambda: "fallback")

    store.create("job1", "input.png", key)
    result = worker_module.enhance_task.run(
        task_id="job1",
        upload_key=key,
        original_filename="input.png",
        scale=2,
    )

    assert result["status"] == "done"
    assert result["backend"] == "fallback"
    raw = store.get("job1")
    assert raw["status"] == TaskStatus.DONE.value
    assert raw["detail"] == "fallback"
    assert raw["result_url"]
    assert raw["result_key"].startswith("tmp/results/imageup/job1/")


def test_enhance_task_records_error(monkeypatch, store, storage, tmp_path):
    key = storage.save_upload("job2", "input.png", make_png_bytes())

    def _boom(*_a, **_k):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(worker_module, "get_storage", lambda: storage)
    monkeypatch.setattr(worker_module, "upscale", _boom)

    store.create("job2", "input.png", key)
    result = worker_module.enhance_task.run(
        task_id="job2",
        upload_key=key,
        original_filename="input.png",
        scale=4,
    )

    assert result["status"] == "error"
    assert "model exploded" in result["detail"]
    raw = store.get("job2")
    assert raw["status"] == TaskStatus.ERROR.value
