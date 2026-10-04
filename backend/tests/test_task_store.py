"""Unit tests for the Redis-backed TaskStore and its pure helpers."""

from __future__ import annotations

import time

import pytest

from app.schemas import TaskStatus
from app.task_store import (
    TaskStore,
    detail_or_none,
    elapsed_from_raw,
    result_or_none,
    status_from_raw,
)


@pytest.fixture()
def store(fake_redis):
    return TaskStore(redis_url="redis://localhost:6379/0", prefix="test:")


def test_create_and_get_roundtrip(store):
    store.create(
        task_id="t1",
        original_filename="photo.png",
        original_path="/tmp/photo.png",
        original_url="/api/results/photo.png",
        status=TaskStatus.PENDING,
    )

    raw = store.get("t1")

    assert raw is not None
    assert raw["task_id"] == "t1"
    assert raw["status"] == "pending"
    assert raw["original_url"] == "/api/results/photo.png"


def test_get_missing_returns_none(store):
    assert store.get("nope") is None


def test_update_sets_fields_and_none_becomes_empty(store):
    store.create("t2", "a.png", "/p/a.png")
    store.update(
        "t2", status=TaskStatus.PROCESSING.value, detail=None, result_url="/r.webp"
    )

    raw = store.get("t2")

    assert raw["status"] == "processing"
    assert raw["detail"] == ""
    assert raw["result_url"] == "/r.webp"


def test_update_to_done_sets_finished_at(store):
    store.create("t3", "a.png", "/p/a.png")
    store.update("t3", status=TaskStatus.DONE.value, result_url="/r.webp")

    raw = store.get("t3")

    assert raw["finished_at"]
    assert float(raw["finished_at"]) > 0


def test_update_with_no_changes_is_a_noop(store):
    store.create("t4", "a.png", "/p/a.png")
    before = store.get("t4")
    store.update("t4")
    assert store.get("t4") == before


def test_delete_removes_task(store):
    store.create("t5", "a.png", "/p/a.png")
    store.delete("t5")
    assert store.get("t5") is None


def test_keys_are_namespaced_by_prefix(store):
    store.create("t6", "a.png", "/p/a.png")
    assert store.redis.exists("test:task:t6") == 1


def test_status_from_raw_handles_unknown_and_missing():
    assert status_from_raw({}) == TaskStatus.PENDING
    assert status_from_raw({"status": "bogus"}) == TaskStatus.PENDING
    assert status_from_raw({"status": "done"}) == TaskStatus.DONE


def test_elapsed_from_raw():
    now = time.time()
    assert elapsed_from_raw({}) is None
    assert elapsed_from_raw(
        {"started_at": str(now - 2), "finished_at": str(now)}
    ) == pytest.approx(2, abs=0.1)
    # running task (no finished_at) returns a positive elapsed
    assert elapsed_from_raw({"started_at": str(now - 1), "finished_at": ""}) > 0
    assert elapsed_from_raw({"started_at": "not-a-number"}) is None


def test_detail_and_result_helpers():
    assert detail_or_none({"detail": ""}) is None
    assert detail_or_none({"detail": "boom"}) == "boom"
    assert result_or_none({"result_url": ""}) is None
    assert result_or_none({"result_url": "/r.webp"}) == "/r.webp"
