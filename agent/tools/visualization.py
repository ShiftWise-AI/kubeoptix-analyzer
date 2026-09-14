"""Ferramentas de geração de gráficos e diagramas para o agente LLM."""

from __future__ import annotations

from pathlib import Path

from agent.analysis.discovery import discover_namespaces
from agent.analysis.topology import analyze_topology
from agent.tools.base import FunctionTool, object_schema
from agent.visualization.pregenerate import (
    NamespaceVisualizations,
    format_visualization_catalog,
    generate_all_visualizations,
)
from agent.visualization.report_assets import ReportAssets


def build_visualization_tools(
    artifacts_dir: Path,
    assets: ReportAssets,
    catalog: list[NamespaceVisualizations],
) -> list[FunctionTool]:
    def list_visualizations() -> str:
        return format_visualization_catalog(catalog)

    def render_composition_chart(
        viz_id: str,
        title: str,
        data: dict[str, int | float],
    ) -> str:
        if not data:
            return "Nenhum dado fornecido para o gráfico."
        normalized = {str(key): float(value) for key, value in data.items()}
        return assets.render_composition(viz_id, title, normalized)

    def render_topology_diagram(namespace: str) -> str:
        namespaces = {ns.name: ns for ns in discover_namespaces(artifacts_dir)}
        ns = namespaces.get(namespace)
        if ns is None:
            available = ", ".join(sorted(namespaces)) or "(nenhum)"
            return f"Namespace '{namespace}' não encontrado. Disponíveis: {available}"
        topo = analyze_topology(ns)
        markdown, engine = assets.render_topology(
            f"{namespace}_topology",
            f"Arquitetura reversa — {namespace}",
            ns,
            topo,
        )
        return f"Engine: {engine}\n\n{markdown}"

    def regenerate_visualizations() -> str:
        nonlocal catalog
        _, catalog = generate_all_visualizations(artifacts_dir)
        return (
            f"Visualizações regeneradas para {len(catalog)} namespace(s).\n\n"
            + format_visualization_catalog(catalog)
        )

    return [
        FunctionTool(
            name="list_visualizations",
            description=(
                "Lista os blocos Markdown de gráficos e diagramas PNG já gerados "
                "em report_assets/. Use para incorporar imagens no relatório."
            ),
            parameters=object_schema({}),
            handler=list_visualizations,
        ),
        FunctionTool(
            name="render_composition_chart",
            description=(
                "Gera um gráfico de composição (donut) em PNG e retorna o Markdown "
                "da imagem para incluir no relatório."
            ),
            parameters=object_schema(
                {
                    "viz_id": {
                        "type": "string",
                        "description": "Identificador único do arquivo (ex.: ns_cpu_limits)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Título exibido no gráfico",
                    },
                    "data": {
                        "type": "object",
                        "description": "Mapa label -> valor numérico",
                        "additionalProperties": {"type": "number"},
                    },
                },
                required=["viz_id", "title", "data"],
            ),
            handler=render_composition_chart,
        ),
        FunctionTool(
            name="render_topology_diagram",
            description=(
                "Gera diagrama de arquitetura PNG (KubeDiagrams ou matplotlib) "
                "para um namespace e retorna o Markdown da imagem."
            ),
            parameters=object_schema(
                {
                    "namespace": {
                        "type": "string",
                        "description": "Nome do namespace OpenShift",
                    }
                },
                required=["namespace"],
            ),
            handler=render_topology_diagram,
        ),
        FunctionTool(
            name="regenerate_visualizations",
            description=(
                "Regenera todos os gráficos e diagramas padrão dos namespaces "
                "e retorna o catálogo Markdown atualizado."
            ),
            parameters=object_schema({}),
            handler=regenerate_visualizations,
        ),
    ]
