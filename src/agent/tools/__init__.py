"""Registry de tools do agente."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.report import ReportBuilder
from agent.tools.base import FunctionTool, object_schema
from agent.tools.filesystem import build_filesystem_tools
from agent.tools.logs import build_log_tools
from agent.tools.manifests import build_manifest_tools


def build_report_tools(report: ReportBuilder) -> list[FunctionTool]:
    def write_report_section(title: str, body: str) -> str:
        report.add_section(title, body)
        return f"Seção '{title}' registrada ({len(body)} chars)."

    return [
        FunctionTool(
            name="write_report_section",
            description=(
                "Adiciona ou atualiza uma seção do relatório final de assessment "
                "(Markdown). Use títulos como 'Resumo executivo', 'Inventário', "
                "'Achados', 'Análise de logs', 'Recomendações'."
            ),
            parameters=object_schema(
                {
                    "title": {
                        "type": "string",
                        "description": "Título da seção",
                    },
                    "body": {
                        "type": "string",
                        "description": "Conteúdo Markdown da seção",
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
) -> list[FunctionTool]:
    tools: list[FunctionTool] = []
    tools.extend(build_filesystem_tools(artifacts_dir, max_file_chars))
    tools.extend(build_manifest_tools(artifacts_dir))
    tools.extend(build_log_tools(artifacts_dir))
    tools.extend(build_report_tools(report))
    return tools


def tools_by_name(tools: list[FunctionTool]) -> dict[str, FunctionTool]:
    return {t.name: t for t in tools}


def openai_tool_schemas(tools: list[FunctionTool]) -> list[dict[str, Any]]:
    return [t.openai_schema() for t in tools]
