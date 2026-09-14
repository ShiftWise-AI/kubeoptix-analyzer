"""Visualizações PNG para relatórios Markdown (matplotlib + KubeDiagrams)."""

from agent.visualization.markdown import (
    embedded_markdown_image,
    embed_markdown_images,
    markdown_image,
)
from agent.visualization.report_assets import ReportAssets

__all__ = [
    "ReportAssets",
    "embedded_markdown_image",
    "embed_markdown_images",
    "markdown_image",
]
