"""Image helpers: format detection, dimension checks, resizing."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image


SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def largest_dimension(img: Image.Image) -> int:
    return max(img.width, img.height)


def save_image(img: Image.Image, path: Path, quality: int) -> None:
    """Save an image preserving transparency for PNG/WebP."""
    fmt = path.suffix.lower().lstrip(".")
    save_kwargs: dict = {}
    if fmt in ("jpg", "jpeg"):
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
    elif fmt == "webp":
        save_kwargs["quality"] = quality
    elif fmt == "png":
        save_kwargs["optimize"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format=fmt.upper() if fmt != "jpg" else "JPEG", **save_kwargs)


def resize_if_too_large(img: Image.Image, max_px: int) -> tuple[Image.Image, bool]:
    """Downscale so the largest side is <= max_px using high-quality Lanczos.
    Returns (image, was_resized)."""
    longest = largest_dimension(img)
    if longest <= max_px:
        return img, False
    scale = max_px / longest
    new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
    return img.resize(new_size, Image.LANCZOS), True


def open_image(path: Path) -> Image.Image:
    img = Image.open(path)
    img.load()
    return img