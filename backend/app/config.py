"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    # Upload limits
    max_upload_mb: int
    allowed_extensions: tuple[str, ...]
    max_input_px: int          # max width OR height, whichever is larger
    output_quality: int        # JPEG/WEBP quality for saved results (1-100)
    output_format: str         # one of: webp, jpg, png

    # CORS
    allowed_origins: tuple[str, ...]

    # ML
    use_gpu: bool
    model_name: str
    enable_ml: bool
    fallback_if_unavailable: bool

    # Storage / TTL
    results_dir: Path
    uploads_dir: Path
    result_ttl_sec: int

    # Celery / Redis
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str
    redis_key_prefix: str

    # Scale factor applied when no explicit factor is supplied
    default_scale: int

    @classmethod
    def from_env(cls) -> "Settings":
        origins = tuple(
            o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()
        )
        base = Path(__file__).resolve().parent.parent
        return cls(
            max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "8")),
            allowed_extensions=tuple(
                e.strip().lower() for e in os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,webp").split(",") if e.strip()
            ),
            max_input_px=int(os.getenv("MAX_INPUT_PX", "1000")),
            output_quality=int(os.getenv("OUTPUT_QUALITY", "95")),
            output_format=os.getenv("OUTPUT_FORMAT", "webp").lower().replace("jpeg", "jpg"),
            allowed_origins=origins,
            use_gpu=os.getenv("USE_GPU", "0") == "1",
            model_name=os.getenv("MODEL_NAME", "RealESRGAN_x4plus"),
            enable_ml=os.getenv("ENABLE_ML", "1") == "1",
            fallback_if_unavailable=os.getenv("FALLBACK_IF_UNAVAILABLE", "1") == "1",
            results_dir=Path(os.getenv("RESULTS_DIR", str(base / "results"))),
            uploads_dir=Path(os.getenv("UPLOADS_DIR", str(base / "uploads"))),
            result_ttl_sec=int(os.getenv("RESULT_TTL_SEC", "3600")),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            celery_broker_url=os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0")),
            celery_result_backend=os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/0")),
            redis_key_prefix=os.getenv("REDIS_KEY_PREFIX", "imageup:"),
            default_scale=int(os.getenv("DEFAULT_SCALE", "2")),
        )

    @property
    def output_extension(self) -> str:
        return self.output_format.replace("jpeg", "jpg")


settings = Settings.from_env()
if settings.output_format not in ("webp", "jpg", "png"):
    raise RuntimeError(f"OUTPUT_FORMAT must be one of webp/jpg/png, got {settings.output_format!r}")
settings.results_dir.mkdir(parents=True, exist_ok=True)
settings.uploads_dir.mkdir(parents=True, exist_ok=True)