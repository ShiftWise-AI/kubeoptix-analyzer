"""Tests for PNG base64 embedding in Markdown reports."""

from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from agent.visualization.markdown import embed_markdown_images, image_search_dirs
from agent.visualization.report_postprocess import postprocess_report_file

_MIN_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

_ARCH_MD = (
    "## 3. Arquitetura reversa\n\n"
    "![Arquitetura KubeOptix — namespace shiftwise-ai](./report_assets/architecture.png)\n"
)


class MarkdownEmbedTests(unittest.TestCase):
    def test_missing_report_dir_leaves_no_embedded_image(self) -> None:
        """Without report_dir, PNGs under reports/report_assets are not embedded."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "assessment" / "shiftwise-ai"
            report_dir = root / "reports"
            artifacts.mkdir(parents=True)
            (report_dir / "report_assets").mkdir(parents=True)
            (report_dir / "report_assets" / "architecture.png").write_bytes(_MIN_PNG)

            result = embed_markdown_images(
                _ARCH_MD,
                search_dirs=image_search_dirs(artifacts, None),
            )
            self.assertNotIn("data:image/png;base64,", result)

    def test_embeds_png_from_report_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "assessment" / "shiftwise-ai"
            report_dir = root / "reports"
            artifacts.mkdir(parents=True)
            (report_dir / "report_assets").mkdir(parents=True)
            (report_dir / "report_assets" / "architecture.png").write_bytes(_MIN_PNG)

            result = embed_markdown_images(
                _ARCH_MD,
                search_dirs=image_search_dirs(artifacts, report_dir),
            )
            self.assertNotIn("./report_assets/", result)
            self.assertIn("data:image/png;base64,", result)

    def test_postprocess_embeds_real_report_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "assessment" / "shiftwise-ai"
            report_dir = root / "reports"
            artifacts.mkdir(parents=True)
            (report_dir / "report_assets").mkdir(parents=True)
            (report_dir / "report_assets" / "architecture.png").write_bytes(_MIN_PNG)
            report_file = report_dir / "shiftwise-ai.md"
            report_file.write_text(_ARCH_MD)

            result = postprocess_report_file(report_file, artifacts)
            content = report_file.read_text()

            self.assertGreaterEqual(result["embedded"], 1)
            self.assertNotIn("./report_assets/", content)
            self.assertIn("data:image/png;base64,", content)


if __name__ == "__main__":
    unittest.main()
