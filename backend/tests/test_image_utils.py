"""Tests for image helper utilities."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.utils.image import (
    get_extension,
    largest_dimension,
    open_image,
    resize_if_too_large,
    save_image,
)


def test_get_extension_normalises_case():
    assert get_extension("Photo.PNG") == ".png"
    assert get_extension("a.b.jpeg") == ".jpeg"
    assert get_extension("noext") == ""


def test_largest_dimension():
    assert largest_dimension(Image.new("RGB", (10, 40))) == 40
    assert largest_dimension(Image.new("RGB", (40, 10))) == 40


def test_resize_if_too_large_noop_when_within_limit():
    img = Image.new("RGB", (50, 30))
    out, resized = resize_if_too_large(img, 100)
    assert resized is False
    assert out.size == (50, 30)


def test_resize_if_too_large_scales_longest_side():
    img = Image.new("RGB", (200, 100))
    out, resized = resize_if_too_large(img, 100)
    assert resized is True
    assert max(out.size) == 100
    assert out.size == (100, 50)


def test_save_image_jpeg_converts_rgba(tmp_path: Path):
    img = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
    dest = tmp_path / "out.jpg"
    save_image(img, dest, quality=80)
    assert dest.exists()
    with Image.open(dest) as saved:
        assert saved.mode == "RGB"


def test_save_image_webp_and_png(tmp_path: Path):
    img = Image.new("RGB", (10, 10), "blue")
    webp = tmp_path / "out.webp"
    png = tmp_path / "out.png"
    save_image(img, webp, quality=90)
    save_image(img, png, quality=90)
    assert webp.exists()
    assert png.exists()


def test_save_image_creates_parent_dirs(tmp_path: Path):
    dest = tmp_path / "nested" / "dir" / "out.png"
    save_image(Image.new("RGB", (5, 5)), dest, quality=90)
    assert dest.exists()


def test_open_image_loads_pixels(tmp_path: Path):
    src = tmp_path / "in.png"
    Image.new("RGB", (7, 9), "green").save(src)
    img = open_image(src)
    assert img.size == (7, 9)
