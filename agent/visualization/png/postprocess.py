"""Pós-processamento de PNGs de relatório."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

from agent.visualization.png.export_config import (
    REPORT_ARCHITECTURE_MAX_HEIGHT_PX,
    REPORT_ARCHITECTURE_MAX_UPSCALE,
    REPORT_ARCHITECTURE_MAX_WIDTH_PX,
    REPORT_ARCHITECTURE_TARGET_WIDTH_PX,
    REPORT_CHART_MAX_HEIGHT_PX,
    REPORT_CHART_MAX_WIDTH_PX,
    REPORT_DIAGRAM_MAX_HEIGHT_PX,
    REPORT_DIAGRAM_MAX_WIDTH_PX,
    LayoutProfile,
)

logger = logging.getLogger(__name__)


def _content_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    rgba = np.asarray(image.convert("RGBA"))
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]
    near_white = np.all(rgb >= 248, axis=2)
    transparent = alpha <= 8
    background = near_white | transparent
    content = ~background
    if not content.any():
        return 0, 0, image.width, image.height
    rows = np.any(content, axis=1)
    cols = np.any(content, axis=0)
    top = int(np.argmax(rows))
    bottom = int(len(rows) - np.argmax(rows[::-1]))
    left = int(np.argmax(cols))
    right = int(len(cols) - np.argmax(cols[::-1]))
    return left, top, right, bottom


def optimize_png_canvas(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    try:
        with Image.open(path) as source:
            orig_w, orig_h = source.size
            left, top, right, bottom = _content_bbox(source)
            content_w = right - left
            content_h = bottom - top
            if content_w <= 0 or content_h <= 0:
                return False
            fill_ratio = (content_w * content_h) / (orig_w * orig_h)
            if fill_ratio >= 0.92:
                return False
            margin = max(3, min(12, int(max(orig_w, orig_h) * 0.012)))
            inner_w = max(1, orig_w - 2 * margin)
            inner_h = max(1, orig_h - 2 * margin)
            scale = min(inner_w / content_w, inner_h / content_h)
            if scale <= 1.0 + 1e-6:
                return False
            cropped = source.crop((left, top, right, bottom))
            new_w = max(1, int(round(content_w * scale)))
            new_h = max(1, int(round(content_h * scale)))
            resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (orig_w, orig_h), (255, 255, 255))
            paste_x = (orig_w - new_w) // 2
            paste_y = (orig_h - new_h) // 2
            canvas.paste(resized.convert("RGB"), (paste_x, paste_y))
            canvas.save(path, format="PNG")
            return True
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        logger.debug("PNG postprocess skipped for %s: %s", path, exc)
        return False


def cap_png_dimensions(path: Path, *, max_width: int, max_height: int) -> bool:
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    try:
        with Image.open(path) as source:
            orig_w, orig_h = source.size
            if orig_w <= max_width and orig_h <= max_height:
                return False
            scale = min(max_width / orig_w, max_height / orig_h)
            new_w = max(1, int(round(orig_w * scale)))
            new_h = max(1, int(round(orig_h * scale)))
            resized = source.resize((new_w, new_h), Image.Resampling.LANCZOS)
            resized.save(path, format="PNG", optimize=True)
            return True
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        logger.debug("PNG resize skipped for %s: %s", path, exc)
        return False


def expand_png_to_target_width(
    path: Path,
    *,
    target_width: int,
    max_height: int,
    max_scale: float = 1.35,
) -> bool:
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    try:
        with Image.open(path) as source:
            orig_w, orig_h = source.size
            if orig_w >= target_width or orig_w <= 0 or orig_h <= 0:
                return False
            scale = min(target_width / orig_w, max_scale)
            new_w = max(1, int(round(orig_w * scale)))
            new_h = max(1, int(round(orig_h * scale)))
            if new_h > max_height:
                fit_scale = max_height / new_h
                new_w = max(1, int(round(new_w * fit_scale)))
                new_h = max(1, int(round(new_h * fit_scale)))
            if new_w <= orig_w and new_h <= orig_h:
                return False
            resized = source.resize((new_w, new_h), Image.Resampling.LANCZOS)
            resized.save(path, format="PNG", optimize=True)
            return True
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        logger.debug("PNG expand skipped for %s: %s", path, exc)
        return False


def finalize_report_png(path: Path, *, profile: LayoutProfile = "chart") -> None:
    if profile == "architecture":
        optimize_png_canvas(path)
        cap_png_dimensions(
            path,
            max_width=REPORT_ARCHITECTURE_MAX_WIDTH_PX,
            max_height=REPORT_ARCHITECTURE_MAX_HEIGHT_PX,
        )
        expand_png_to_target_width(
            path,
            target_width=REPORT_ARCHITECTURE_TARGET_WIDTH_PX,
            max_height=REPORT_ARCHITECTURE_MAX_HEIGHT_PX,
            max_scale=REPORT_ARCHITECTURE_MAX_UPSCALE,
        )
        return
    optimize_png_canvas(path)
    if profile == "diagram":
        cap_png_dimensions(
            path,
            max_width=REPORT_DIAGRAM_MAX_WIDTH_PX,
            max_height=REPORT_DIAGRAM_MAX_HEIGHT_PX,
        )
        return
    cap_png_dimensions(
        path,
        max_width=REPORT_CHART_MAX_WIDTH_PX,
        max_height=REPORT_CHART_MAX_HEIGHT_PX,
    )
