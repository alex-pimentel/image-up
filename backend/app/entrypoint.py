#!/usr/bin/env python3
"""Container entrypoint: download Real-ESRGAN model weights on first start,
then exec the passed command (uvicorn for API, celery for worker).

Weights are cached in /app/models so subsequent restarts skip the download.

Set MD_ENABLE_ML=0 to skip ML entirely and run in fallback mode.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/app/models"))
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Map of supported model name -> download URL. The realesrgan package hosts
# the official xintao weights on GitHub releases.
MODELS = {
    "RealESRGAN_x4plus": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    "RealESRGAN_x4plus_anime_6B": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
}


def download(path: Path, url: str) -> None:
    import urllib.request

    print(f"[entrypoint] downloading {url} -> {path}", flush=True)
    # Unique part name per process to avoid races between backend & worker
    # containers sharing the same /app/models volume.
    tmp = path.with_suffix(f".pth.part.{os.getpid()}")
    try:
        urllib.request.urlretrieve(url, tmp)  # nosec - downloading model weights from GitHub releases
        # Another container may have just finished writing the destination.
        if path.exists() and path.stat().st_size > 0:
            print(f"[entrypoint] {path.name} already written by a peer; discarding local copy", flush=True)
            return
        os.replace(tmp, path)
        print(f"[entrypoint] saved {path} ({path.stat().st_size // 1024 // 1024}MB)", flush=True)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def main() -> None:
    enable = os.environ.get("ENABLE_ML", "1") == "1"
    if not enable:
        print("[entrypoint] ENABLE_ML=0 -> skipping model download", flush=True)
    else:
        name = os.environ.get("MODEL_NAME", "RealESRGAN_x4plus")
        url = MODELS.get(name)
        if not url:
            print(f"[entrypoint] unknown MODEL_NAME={name}; skipping", flush=True)
        else:
            path = MODELS_DIR / f"{name}.pth"
            if path.exists() and path.stat().st_size > 0:
                print(f"[entrypoint] {name} already present ({path.stat().st_size // 1024 // 1024}MB)", flush=True)
            else:
                try:
                    download(path, url)
                except Exception as e:
                    print(f"[entrypoint] download failed ({e}); the worker will run in fallback mode", flush=True)

    cmd = sys.argv[1:]
    if not cmd:
        cmd = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

    # Replace this process with the requested command.
    os.execvp(cmd[0], cmd)  # nosec - standard Docker entrypoint pattern


if __name__ == "__main__":
    main()