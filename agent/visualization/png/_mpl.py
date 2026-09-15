"""Configuração compartilhada do matplotlib (backend headless)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from agent.visualization.png.export_config import REPORT_IMAGE_DPI, LayoutProfile
from agent.visualization.png.postprocess import finalize_report_png

DEFAULT_FIGURE_DPI = REPORT_IMAGE_DPI
DEFAULT_PAD_INCHES = 0.02


def save_figure(
    fig,
    output_path: Path,
    *,
    dpi: int = DEFAULT_FIGURE_DPI,
    profile: LayoutProfile = "chart",
) -> None:
    fig.savefig(
        output_path,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=DEFAULT_PAD_INCHES,
        facecolor=fig.get_facecolor(),
        edgecolor="none",
    )
    finalize_report_png(output_path, profile=profile)
