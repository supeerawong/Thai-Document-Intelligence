from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps


@dataclass(frozen=True, slots=True)
class ImagePreprocessingOptions:
    """Conservative preprocessing suitable for Thai document OCR."""

    enabled: bool = True
    grayscale: bool = True
    autocontrast: bool = True
    denoise: bool = False
    binarize: bool = False
    min_width: int = 1600
    max_upscale: float = 2.0


def _otsu_threshold(image: Image.Image) -> int:
    histogram = image.histogram()[:256]
    total = sum(histogram)
    weighted_sum = sum(index * count for index, count in enumerate(histogram))
    background_weight = 0
    background_sum = 0
    best_variance = -1.0
    threshold = 127
    for index, count in enumerate(histogram):
        background_weight += count
        if background_weight == 0:
            continue
        foreground_weight = total - background_weight
        if foreground_weight == 0:
            break
        background_sum += index * count
        background_mean = background_sum / background_weight
        foreground_mean = (weighted_sum - background_sum) / foreground_weight
        variance = background_weight * foreground_weight * (background_mean - foreground_mean) ** 2
        if variance > best_variance:
            best_variance = variance
            threshold = index
    return threshold


def preprocess_image(
    image: Image.Image,
    options: ImagePreprocessingOptions | None = None,
) -> Image.Image:
    """Prepare an image without mutating the caller-owned object."""

    config = options or ImagePreprocessingOptions()
    prepared = ImageOps.exif_transpose(image).copy()
    if not config.enabled:
        return prepared.convert("RGB")

    if prepared.width < config.min_width:
        scale = min(config.max_upscale, config.min_width / max(prepared.width, 1))
        if scale > 1:
            prepared = prepared.resize(
                (round(prepared.width * scale), round(prepared.height * scale)),
                Image.Resampling.LANCZOS,
            )
    if config.grayscale:
        prepared = ImageOps.grayscale(prepared)
    if config.autocontrast:
        prepared = ImageOps.autocontrast(prepared, cutoff=1)
    if config.denoise:
        prepared = prepared.filter(ImageFilter.MedianFilter(size=3))
    if config.binarize:
        grayscale = prepared if prepared.mode == "L" else ImageOps.grayscale(prepared)
        threshold = _otsu_threshold(grayscale)
        prepared = grayscale.point(lambda value: 255 if value > threshold else 0)
    return prepared
