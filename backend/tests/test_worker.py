"""Tests for the Celery worker task.

The ML upscaler is patched out so the task can be driven as a plain function
while still exercising task-store transitions (processing -> done/error).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import worker as worker_module
from app.schemas import TaskStatus
from app.task_store import TaskStore
from tests.conftest import make_png_bytes, patch_settings


@pytest.fixture()
def input_image(tmp_path: Path) -> Path:
    path = tmp_path / "input.png"
    path.write_bytes(make_png_bytes())
    return path


@pytest.fixture()
def store(fake_redis):
    # Use the same key prefix as the worker's internally-constructed TaskStore.
    return TaskStore(redis_url="redis://localhost:6379/0")


def test_enhance_task_marks_done(monkeypatch, store, input_image, tmp_path):
    results = tmp_path / "results"
    results.mkdir(parents=True, exist_ok=True)
    patch_settings(monkeypatch, worker_module, results_dir=results)
    monkeypatch.setattr(worker_module, "upscale", lambda *a, **k: None)
    monkeypatch.setattr(worker_module, "backend_label", lambda: "fallback")

    store.create("job1", "input.png", str(input_image))
    result = worker_module.enhance_task.run(
        task_id="job1",
        input_path=str(input_image),
        original_filename="input.png",
        scale=2,
    )

    assert result["status"] == "done"
    assert result["backend"] == "fallback"
    raw = store.get("job1")
    assert raw["status"] == TaskStatus.DONE.value
    assert raw["detail"] == "fallback"
    assert raw["result_url"]


def test_enhance_task_records_error(monkeypatch, store, input_image, tmp_path):
    results = tmp_path / "results"
    results.mkdir(parents=True, exist_ok=True)
    patch_settings(monkeypatch, worker_module, results_dir=results)

    def _boom(*_a, **_k):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(worker_module, "upscale", _boom)

    store.create("job2", "input.png", str(input_image))
    result = worker_module.enhance_task.run(
        task_id="job2",
        input_path=str(input_image),
        original_filename="input.png",
        scale=4,
    )

    assert result["status"] == "error"
    assert "model exploded" in result["detail"]
    raw = store.get("job2")
    assert raw["status"] == TaskStatus.ERROR.value
