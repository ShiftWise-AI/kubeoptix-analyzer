"""Markdown report assembly and persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from agent.visualization.markdown import embed_markdown_images


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
            "# Relatório de assessment OpenShift",
            "",
            f"_Gerado em {now}_",
            f"_Artefatos: `{self.artifacts_dir}`_",
            "",
        ]
        if not self.sections:
            lines.extend(
                [
                    "## Sem seções",
                    "",
                    "O agente não registrou seções via `write_report_section`.",
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

    def write(self, filename: str = "assessment-report.md") -> Path:
        out = self.artifacts_dir / filename
        content = embed_markdown_images(self.render(), markdown_dir=self.artifacts_dir)
        out.write_text(content, encoding="utf-8")
        return out
