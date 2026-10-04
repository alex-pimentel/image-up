"""Tests for the storage abstraction (local fallback + R2 adapter)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.services import storage as storage_module
from app.services.r2 import R2Storage
from app.services.storage import (
    LocalStorageAdapter,
    R2StorageAdapter,
    content_type_for,
    get_storage,
    reset_storage,
)
from tests.test_r2 import FakeS3Client


def _fake_r2() -> tuple[R2StorageAdapter, FakeS3Client]:
    client = FakeS3Client()
    r2 = R2Storage(
        bucket="agenteresolve-tmp",
        endpoint="https://acct.r2.cloudflarestorage.com",
        access_key_id="id",
        secret_access_key="secret",
        presign_expiry_sec=120,
        client=client,
    )
    return R2StorageAdapter(r2), client


def test_content_type_for_known_and_unknown() -> None:
    assert content_type_for("a.webp") == "image/webp"
    assert content_type_for("a.JPG") == "image/jpeg"
    assert content_type_for("a.png") == "image/png"
    assert content_type_for("a.bin") == "application/octet-stream"


def test_r2_adapter_roundtrip(tmp_path: Path) -> None:
    adapter, client = _fake_r2()

    key = adapter.save_upload("t1", "photo.png", b"original")
    assert key == "tmp/uploads/imageup/t1/photo.png"
    assert client.objects[key] == b"original"

    src = tmp_path / "result.webp"
    src.write_bytes(b"enhanced")
    result_key = adapter.save_result("t1", src)
    assert result_key == "tmp/results/imageup/t1/result.webp"

    dest = tmp_path / "out" / "photo.png"
    adapter.fetch_upload(key, dest)
    assert dest.read_bytes() == b"original"

    response = adapter.response_for(result_key)
    assert response.status_code == 302
    assert response.headers["location"].startswith("https://r2.example/")
    assert adapter.is_remote is True


def test_local_adapter_roundtrip(tmp_path: Path) -> None:
    adapter = LocalStorageAdapter(tmp_path)
    key = adapter.save_upload("t2", "photo.png", b"original")
    assert adapter.is_remote is False

    src = tmp_path / "result.webp"
    src.write_bytes(b"enhanced")
    result_key = adapter.save_result("t2", src)

    dest = tmp_path / "nested" / "copy.png"
    adapter.fetch_upload(key, dest)
    assert dest.read_bytes() == b"original"

    response = adapter.response_for(result_key)
    assert response.status_code == 200


def test_local_adapter_response_for_missing(tmp_path: Path) -> None:
    adapter = LocalStorageAdapter(tmp_path)
    with pytest.raises(HTTPException) as exc:
        adapter.response_for("tmp/results/imageup/nope/result.webp")
    assert exc.value.status_code == 404


def test_get_storage_returns_r2_when_configured(monkeypatch, tmp_path: Path) -> None:
    new_settings = dataclasses.replace(
        storage_module.settings,
        r2_access_key_id="id",
        r2_secret_access_key="secret",
        r2_endpoint="https://acct.r2.cloudflarestorage.com",
        storage_dir=tmp_path,
    )
    monkeypatch.setattr(storage_module, "settings", new_settings)
    reset_storage()
    try:
        adapter = get_storage()
        assert isinstance(adapter, R2StorageAdapter)
        assert get_storage() is adapter  # cached
    finally:
        reset_storage()


def test_get_storage_falls_back_to_local(monkeypatch, tmp_path: Path) -> None:
    new_settings = dataclasses.replace(
        storage_module.settings,
        r2_access_key_id="",
        r2_secret_access_key="",
        r2_endpoint="",
        storage_dir=tmp_path,
    )
    monkeypatch.setattr(storage_module, "settings", new_settings)
    reset_storage()
    try:
        adapter = get_storage()
        assert isinstance(adapter, LocalStorageAdapter)
    finally:
        reset_storage()
