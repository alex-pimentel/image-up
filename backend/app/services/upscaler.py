"""Upscaling service: Real-ESRGAN when available, PIL fallback otherwise.

The ML backend is imported lazily so the service can still run (in fallback
mode) on machines without torch / realesrgan installed. This keeps the API
contract working end-to-end for local dev, CI, and small VPSes.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PIL import Image, ImageFilter

from ..config import settings
from ..utils.image import save_image

logger = logging.getLogger(__name__)

# Reusable unsharp-mask filter for the fallback upscaler.
_UNSHARP = ImageFilter.UnsharpMask(radius=2, percent=160, threshold=3)

# Cached singletons
_ml_backend: Optional["MLBackend"] = None
_ml_available: Optional[bool] = None


class MLBackend:
    """Wraps the Real-ESRGAN python inference API."""

    def __init__(self, model_name: str, use_gpu: bool) -> None:
        from realesrgan import RealESRGANer
        from basicsr.archs.rrdbnet_arch import RRDBNet

        # Pick a model architecture based on the configured name.
        if model_name == "RealESRGAN_x4plus_anime_6B":
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
        else:  # default RealESRGAN_x4plus
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)

        models_dir = Path(__file__).resolve().parent.parent.parent / "models"
        candidate = str(models_dir / f"{model_name}.pth")
        model_path: str | None = candidate if Path(candidate).exists() else None

        self.upsampler = RealESRGANer(
            scale=4,
            model_path=model_path,
            model=model,
            tile=0,
            tile_pad=10,
            pre_pad=0,
            half=False,
            gpu_id=0 if use_gpu else None,
            device="cuda" if use_gpu else "cpu",
        )
        self.model_name = model_name

    def enhance(self, img: Image.Image, out_scale: int = 4) -> Image.Image:
        import numpy as np

        arr = np.array(img.convert("RGB"))
        out, _ = self.upsampler.enhance(arr, outscale=out_scale)
        return Image.fromarray(out)


def is_ml_available() -> bool:
    global _ml_available
    if _ml_available is not None:
        return _ml_available
    if not settings.enable_ml:
        _ml_available = False
        return _ml_available
    try:
        import torch  # noqa: F401
        import realesrgan  # noqa: F401
        import basicsr  # noqa: F401
        _ml_available = True
    except Exception as e:  # pragma: no cover - environment dependent
        logger.warning("ML backend unavailable, using fallback: %s", e)
        _ml_available = False
    return _ml_available


def get_backend() -> "MLBackend":
    global _ml_backend
    if _ml_backend is None:
        _ml_backend = MLBackend(settings.model_name, settings.use_gpu)
    return _ml_backend


def backend_label() -> str:
    return "ml" if is_ml_available() else "fallback"


def upscale(input_path: Path, output_path: Path, scale: int = 4) -> Image.Image:
    """Upscale the image at input_path and save to output_path. Returns the result PIL image."""
    from ..utils.image import open_image

    img = open_image(input_path)

    if is_ml_available():
        try:
            backend = get_backend()
            result = backend.enhance(img, out_scale=scale)
        except Exception as e:
            logger.exception("ML enhance failed: %s", e)
            if settings.fallback_if_unavailable:
                result = _fallback_upscale(img, scale)
            else:
                raise
    else:
        result = _fallback_upscale(img, scale)

    save_image(result, output_path, settings.output_quality)
    return result


def _fallback_upscale(img: Image.Image, scale: int) -> Image.Image:
    """Lanczos upscaling + unsharp mask used when the ML model is unavailable.
    The browser will bilinearly upscale the small original for the "before"
    view; this produces a visibly crisper "after" so the difference is obvious
    even without the heavy ML deps installed."""
    new_size = (img.width * scale, img.height * scale)
    up = img.resize(new_size, Image.Resampling.LANCZOS)
    # Unsharp mask: (radius, percent, threshold). Mild but noticeable.
    try:
        up = up.filter(_UNSHARP)
    except Exception:  # nosec - unsharp mask is a nice-to-have enhancement
        pass
    return up