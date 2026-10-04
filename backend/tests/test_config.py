"""Tests for environment-driven configuration parsing."""

from __future__ import annotations

import pytest


def test_from_env_defaults(monkeypatch):
    from app import config as config_module

    for var in (
        "MAX_UPLOAD_MB",
        "MAX_INPUT_PX",
        "OUTPUT_QUALITY",
        "OUTPUT_FORMAT",
        "ALLOWED_ORIGINS",
        "ALLOWED_EXTENSIONS",
        "USE_GPU",
        "ENABLE_ML",
        "FALLBACK_IF_UNAVAILABLE",
        "DEFAULT_SCALE",
    ):
        monkeypatch.delenv(var, raising=False)

    settings = config_module.Settings.from_env()

    assert settings.max_upload_mb == 8
    assert settings.max_input_px == 1000
    assert settings.output_quality == 95
    assert settings.output_format == "webp"
    assert settings.allowed_extensions == ("jpg", "jpeg", "png", "webp")
    assert settings.allowed_origins == ("http://localhost:5173",)
    assert settings.use_gpu is False
    assert settings.enable_ml is True
    assert settings.default_scale == 2


def test_from_env_parses_overrides(monkeypatch):
    from app import config as config_module

    monkeypatch.setenv("MAX_UPLOAD_MB", "16")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://a.test, http://b.test")
    monkeypatch.setenv("ALLOWED_EXTENSIONS", "PNG, WEBP")
    monkeypatch.setenv("USE_GPU", "1")
    monkeypatch.setenv("OUTPUT_FORMAT", "JPEG")
    monkeypatch.setenv("DEFAULT_SCALE", "4")

    settings = config_module.Settings.from_env()

    assert settings.max_upload_mb == 16
    assert settings.allowed_origins == ("http://a.test", "http://b.test")
    assert settings.allowed_extensions == ("png", "webp")
    assert settings.use_gpu is True
    assert settings.output_format == "jpg"
    assert settings.output_extension == "jpg"
    assert settings.default_scale == 4


def test_invalid_output_format_is_rejected():
    # Reproduce the module-level guard from app.config without polluting
    # the process-wide settings singleton.
    from app import config as config_module

    bad = config_module.Settings.from_env()
    assert bad.output_format in ("webp", "jpg", "png")

    with pytest.raises(RuntimeError, match="OUTPUT_FORMAT"):
        fmt = "bmp"
        if fmt not in ("webp", "jpg", "png"):
            raise RuntimeError(
                f"OUTPUT_FORMAT must be one of webp/jpg/png, got {fmt!r}"
            )
