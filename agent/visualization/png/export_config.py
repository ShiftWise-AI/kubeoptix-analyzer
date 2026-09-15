"""Parâmetros de exportação PNG para relatórios Markdown."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from agent.visualization.chart_theme import CHART_MAX_WIDTH

LayoutProfile = Literal["chart", "diagram", "architecture"]

REPORT_IMAGE_DPI = 120
REPORT_CHART_MAX_WIDTH_PX = CHART_MAX_WIDTH
REPORT_CHART_MAX_HEIGHT_PX = 420
REPORT_DIAGRAM_MAX_WIDTH_PX = 960
REPORT_DIAGRAM_MAX_HEIGHT_PX = 540
REPORT_ARCHITECTURE_DPI = 120
REPORT_ARCHITECTURE_PAGE_WIDTH_IN = 16.0
REPORT_ARCHITECTURE_PAGE_HEIGHT_IN = 6.5
REPORT_ARCHITECTURE_MAX_WIDTH_PX = 1600
REPORT_ARCHITECTURE_MAX_HEIGHT_PX = 720
REPORT_ARCHITECTURE_TARGET_WIDTH_PX = 1600
REPORT_ARCHITECTURE_MAX_UPSCALE = 2.5

EMPTY_CHART_FIGSIZE = (5.0, 2.5)
COMPOSITION_FIGSIZE = (6.5, 3.75)

WIDE_DIAGRAM_VIZ_IDS = frozenset({"namespace_topology", "namespace_architecture"})


def layout_profile_for_output(output_path: Path) -> LayoutProfile:
    if output_path.stem in WIDE_DIAGRAM_VIZ_IDS:
        return "architecture"
    return "diagram"


def flowchart_figsize(x_extent: float, y_extent: float) -> tuple[float, float]:
    width = max(10.0, min(16.0, x_extent * 0.95))
    height = max(3.2, min(6.5, y_extent + 0.8))
    return width, height
