"""Markdown report assembly and persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from agent.i18n import t
from agent.visualization.pregenerate import (
    NamespaceVisualizations,
    finalize_report_markdown,
)


@dataclass
class ReportBuilder:
    artifacts_dir: Path
    sections: list[tuple[str, str]] = field(default_factory=list)

    def add_section(self, title: str, body: str) -> None:
        title = title.strip()
        body = body.strip()
        if not title:
            raise ValueError("Section title cannot be empty")
        # Update an existing section with the same title.
        for idx, (existing_title, _) in enumerate(self.sections):
            if existing_title.lower() == title.lower():
                self.sections[idx] = (title, body)
                return
        self.sections.append((title, body))

    def render(self) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            t("report.title"),
            "",
            t("report.generated", when=now),
            t("report.artifacts", path=self.artifacts_dir),
            "",
        ]
        if not self.sections:
            lines.extend(
                [
                    t("report.no_sections"),
                    "",
                    t("report.no_sections_body"),
                    "",
                ]
            )
        else:
            for title, body in self.sections:
                lines.append(f"## {title}")
                lines.append("")
                lines.append(body)
                lines.append("")
        return "\n".join(lines)

    def write(
        self,
        filename: str = "assessment-report.md",
        *,
        visualizations: list[NamespaceVisualizations] | None = None,
    ) -> Path:
        out = self.artifacts_dir / filename
        content = finalize_report_markdown(
            self.render(),
            artifacts_dir=self.artifacts_dir,
            visualizations=visualizations,
        )
        out.write_text(content, encoding="utf-8")
        return out
