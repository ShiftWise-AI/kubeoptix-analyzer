"""Registry of agent tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.report import ReportBuilder
from agent.tools.base import FunctionTool, object_schema
from agent.tools.filesystem import build_filesystem_tools
from agent.tools.logs import build_log_tools
from agent.tools.manifests import build_manifest_tools
from agent.tools.visualization import build_visualization_tools
from agent.visualization.pregenerate import NamespaceVisualizations
from agent.visualization.report_assets import ReportAssets


def build_report_tools(report: ReportBuilder) -> list[FunctionTool]:
    def write_report_section(title: str, body: str) -> str:
        report.add_section(title, body)
        return f"Section '{title}' registered ({len(body)} chars)."

    return [
        FunctionTool(
            name="write_report_section",
            description=(
                "Adds or updates a section in the final assessment report "
                "(Markdown). Use titles such as 'Executive summary', 'Inventory', "
                "'Findings', 'Log analysis', and 'Recommendations'."
            ),
            parameters=object_schema(
                {
                    "title": {
                        "type": "string",
                        "description": "Section title",
                    },
                    "body": {
                        "type": "string",
                        "description": "Markdown body for the section",
                    },
                },
                required=["title", "body"],
            ),
            handler=write_report_section,
        )
    ]


def build_all_tools(
    artifacts_dir: Path,
    report: ReportBuilder,
    max_file_chars: int,
    *,
    assets: ReportAssets,
    visualizations: list[NamespaceVisualizations],
) -> list[FunctionTool]:
    tools: list[FunctionTool] = []
    tools.extend(build_filesystem_tools(artifacts_dir, max_file_chars))
    tools.extend(build_manifest_tools(artifacts_dir))
    tools.extend(build_log_tools(artifacts_dir))
    tools.extend(build_visualization_tools(artifacts_dir, assets, visualizations))
    tools.extend(build_report_tools(report))
    return tools


def tools_by_name(tools: list[FunctionTool]) -> dict[str, FunctionTool]:
    return {t.name: t for t in tools}


def openai_tool_schemas(tools: list[FunctionTool]) -> list[dict[str, Any]]:
    return [t.openai_schema() for t in tools]
