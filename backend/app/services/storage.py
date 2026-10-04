"""Storage abstraction used by the API and the worker.

Production uses Cloudflare R2 (private ``tmp`` bucket, 24h lifecycle). When the
``R2_*`` credentials are absent (local dev, CI) it transparently falls back to
local disk so the end-to-end flow keeps working without cloud access.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response

from ..config import settings
from .r2 import R2Storage, result_key, upload_key

logger = logging.getLogger(__name__)

_CONTENT_TYPES = {
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def content_type_for(filename: str) -> str:
    return _CONTENT_TYPES.get(Path(filename).suffix.lower(), "application/octet-stream")


class R2StorageAdapter:
    is_remote = True

    def __init__(self, r2: R2Storage) -> None:
        self.r2 = r2

    def save_upload(self, task_id: str, filename: str, data: bytes) -> str:
        key = upload_key(task_id, filename)
        self.r2.put_bytes(key, data, content_type=content_type_for(filename))
        return key

    def save_result(self, task_id: str, src_path: Path) -> str:
        key = result_key(task_id, Path(src_path).name)
        self.r2.put_file(key, src_path, content_type=content_type_for(key))
        return key

    def fetch_upload(self, key: str, dest: Path) -> None:
        self.r2.download_file(key, dest)

    def response_for(self, key: str) -> Response:
        return RedirectResponse(self.r2.presigned_get_url(key), status_code=302)


class LocalStorageAdapter:
    """Disk fallback that mirrors the R2 key layout under ``storage_dir``."""

    is_remote = False

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / key

    def save_upload(self, task_id: str, filename: str, data: bytes) -> str:
        key = upload_key(task_id, filename)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def save_result(self, task_id: str, src_path: Path) -> str:
        key = result_key(task_id, Path(src_path).name)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(Path(src_path).read_bytes())
        return key

    def fetch_upload(self, key: str, dest: Path) -> None:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self._path(key).read_bytes())

    def response_for(self, key: str) -> Response:
        path = self._path(key)
        if not path.exists():
            raise HTTPException(
                status_code=404, detail="Object not found (may have expired)."
            )
        return FileResponse(path, media_type=content_type_for(key))


Storage = R2StorageAdapter | LocalStorageAdapter

_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        if settings.r2_enabled:
            _storage = R2StorageAdapter(
                R2Storage(
                    bucket=settings.r2_bucket_tmp,
                    endpoint=settings.r2_endpoint,
                    access_key_id=settings.r2_access_key_id,
                    secret_access_key=settings.r2_secret_access_key,
                    presign_expiry_sec=settings.r2_presign_expiry_sec,
                )
            )
        else:
            logger.warning(
                "R2 is not configured; using local disk storage (development fallback)"
            )
            _storage = LocalStorageAdapter(settings.storage_dir)
    return _storage


def reset_storage() -> None:
    """Drop the cached storage backend (used by tests)."""
    global _storage
    _storage = None
