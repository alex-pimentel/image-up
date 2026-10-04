"""Integration tests for the FastAPI surface.

Covers the enhance -> queue -> status flow with a mocked Celery task and an
in-memory Redis task store, plus the health/config endpoints and validation.
"""

from __future__ import annotations

from tests.conftest import make_png_bytes


def test_health_reports_fallback_backend(api_client):
    resp = api_client.get("/api/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["backend"] in ("ml", "fallback")
    assert isinstance(body["ml_available"], bool)


def test_config_exposes_limits(api_client):
    resp = api_client.get("/api/config")

    assert resp.status_code == 200
    body = resp.json()
    assert body["max_upload_mb"] > 0
    assert "png" in body["allowed_extensions"]
    assert body["output_format"] in ("webp", "jpg", "png")


def test_enhance_enqueues_task_and_returns_pending(api_client):
    resp = api_client.post(
        "/api/enhance?scale=2",
        files={"file": ("photo.png", make_png_bytes(), "image/png")},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert body["task_id"]
    assert len(api_client.enqueued) == 1
    call = api_client.enqueued[0]
    assert call["kwargs"]["task_id"] == body["task_id"]
    assert call["kwargs"]["scale"] == 2
    assert call["queue"] == "imageup"


def test_enhance_then_status_reflects_task(api_client):
    enhance = api_client.post(
        "/api/enhance?scale=4",
        files={"file": ("photo.png", make_png_bytes(), "image/png")},
    )
    task_id = enhance.json()["task_id"]

    status = api_client.get(f"/api/status/{task_id}")

    assert status.status_code == 200
    body = status.json()
    assert body["task_id"] == task_id
    assert body["status"] == "pending"
    assert body["original_filename"] == "photo.png"
    assert body["original_url"].endswith(".png")


def test_status_unknown_task_returns_404(api_client):
    resp = api_client.get("/api/status/does-not-exist")

    assert resp.status_code == 404


def test_enhance_rejects_unsupported_extension(api_client):
    resp = api_client.post(
        "/api/enhance",
        files={"file": ("photo.gif", b"gif89a", "image/gif")},
    )

    assert resp.status_code == 415


def test_enhance_rejects_invalid_scale(api_client):
    resp = api_client.post(
        "/api/enhance?scale=3",
        files={"file": ("photo.png", make_png_bytes(), "image/png")},
    )

    assert resp.status_code == 422


def test_enhance_rejects_oversized_image(api_client, monkeypatch):
    from app import main as main_module
    from tests.conftest import patch_settings

    patch_settings(monkeypatch, main_module, max_input_px=4)

    resp = api_client.post(
        "/api/enhance",
        files={"file": ("photo.png", make_png_bytes(16, 16), "image/png")},
    )

    assert resp.status_code == 422
    assert "too large" in resp.json()["detail"].lower()


def test_enhance_rejects_corrupt_image(api_client):
    resp = api_client.post(
        "/api/enhance",
        files={"file": ("photo.png", b"not-an-image", "image/png")},
    )

    assert resp.status_code == 422


def test_enhance_rejects_file_over_size_limit(api_client, monkeypatch):
    from app import main as main_module
    from tests.conftest import patch_settings

    patch_settings(monkeypatch, main_module, max_upload_mb=0)

    resp = api_client.post(
        "/api/enhance",
        files={"file": ("photo.png", make_png_bytes(), "image/png")},
    )

    assert resp.status_code == 413
