"""Pré-geração de gráficos e diagramas para relatórios com LLM."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent.analysis.discovery import NamespaceArtifacts, discover_namespaces, list_apps
from agent.analysis.observability import analyze_observability
from agent.analysis.resources import analyze_resources
from agent.analysis.topology import analyze_topology
from agent.analysis.worknodes import discover_worknodes
from agent.visualization.markdown import embed_markdown_images, strip_unresolvable_image_refs
from agent.visualization.report_assets import ReportAssets


@dataclass(frozen=True)
class NamespaceVisualizations:
    namespace: str
    topology_md: str
    memory_chart_md: str
    cpu_chart_md: str
    errors_by_app_md: str
    errors_by_category_md: str


def _render_namespace_visualizations(
    ns: NamespaceArtifacts,
    assets: ReportAssets,
    worknodes,
) -> NamespaceVisualizations:
    apps = list_apps(ns)
    topo = analyze_topology(ns)
    resources = analyze_resources(ns, worknodes=worknodes)
    obs = analyze_observability(ns, apps)

    topology_md, _ = assets.render_topology(
        f"{ns.name}_topology",
        f"Arquitetura reversa — {ns.name}",
        ns,
        topo,
    )

    mem_counter = {
        app: int(round(summary.mem_lim_mi))
        for app, summary in resources.by_app.items()
        if summary.mem_lim_mi > 0
    }
    cpu_counter = {
        app: int(round(summary.cpu_lim_m))
        for app, summary in resources.by_app.items()
        if summary.cpu_lim_m > 0
    }

    memory_chart_md = assets.render_composition(
        f"{ns.name}_mem_limits_by_app",
        "Memória limits (Mi) por aplicação",
        mem_counter,
    )
    cpu_chart_md = assets.render_composition(
        f"{ns.name}_cpu_limits_by_app",
        "CPU limits (m) por aplicação",
        cpu_counter,
    )
    errors_by_app_md = assets.render_composition(
        f"{ns.name}_errors_by_app",
        "Erros por aplicação",
        obs.errors_by_app,
        include_other=True,
    )
    errors_by_category_md = assets.render_composition(
        f"{ns.name}_errors_by_category",
        "Erros por categoria",
        obs.errors_by_category,
        include_other=True,
    )

    return NamespaceVisualizations(
        namespace=ns.name,
        topology_md=topology_md,
        memory_chart_md=memory_chart_md,
        cpu_chart_md=cpu_chart_md,
        errors_by_app_md=errors_by_app_md,
        errors_by_category_md=errors_by_category_md,
    )


def generate_all_visualizations(
    artifacts_dir: Path,
) -> tuple[ReportAssets, list[NamespaceVisualizations]]:
    assets = ReportAssets(assets_dir=artifacts_dir / "report_assets")
    worknodes = discover_worknodes(artifacts_dir)
    namespaces = discover_namespaces(artifacts_dir)
    results = [
        _render_namespace_visualizations(ns, assets, worknodes) for ns in namespaces
    ]
    return assets, results


def format_visualization_catalog(
    visualizations: list[NamespaceVisualizations],
) -> str:
    if not visualizations:
        return "Nenhuma visualização foi gerada (nenhum namespace encontrado)."

    lines = [
        "As visualizações abaixo já foram renderizadas em PNG em `report_assets/`.",
        "Inclua os blocos Markdown correspondentes nas seções adequadas do relatório "
        "(arquitetura, recursos, observabilidade). Não use Mermaid.",
        "",
    ]
    for viz in visualizations:
        lines.extend(
            [
                f"### Namespace `{viz.namespace}` — diagrama de arquitetura",
                "",
                viz.topology_md,
                "",
                f"### Namespace `{viz.namespace}` — memória limits por aplicação",
                "",
                viz.memory_chart_md,
                "",
                f"### Namespace `{viz.namespace}` — CPU limits por aplicação",
                "",
                viz.cpu_chart_md,
                "",
                f"### Namespace `{viz.namespace}` — erros por aplicação",
                "",
                viz.errors_by_app_md,
                "",
                f"### Namespace `{viz.namespace}` — erros por categoria",
                "",
                viz.errors_by_category_md,
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _report_has_embedded_images(content: str) -> bool:
    return "data:image/png;base64," in content


def embedded_image_count(content: str) -> int:
    return content.count("data:image/png;base64,")


def append_visualizations_to_markdown(
    content: str,
    visualizations: list[NamespaceVisualizations],
) -> str:
    """Anexa visualizações pré-geradas quando o relatório ainda não tem PNGs embutidos."""
    if not visualizations or _report_has_embedded_images(content):
        return content
    catalog = format_visualization_catalog(visualizations)
    return f"{content.rstrip()}\n\n## Visualizações\n\n{catalog}\n"


def append_missing_visualizations(
    sections: list[tuple[str, str]],
    visualizations: list[NamespaceVisualizations],
) -> list[tuple[str, str]]:
    """Garante que o relatório referencia PNGs quando o LLM não os incluiu."""
    body = "\n".join(text for _, text in sections)
    if not visualizations or _report_has_embedded_images(body):
        return sections

    catalog = format_visualization_catalog(visualizations)
    updated = list(sections)
    updated.append(("Visualizações", catalog))
    return updated


def finalize_report_markdown(
    content: str,
    *,
    artifacts_dir: Path,
    visualizations: list[NamespaceVisualizations] | None = None,
) -> str:
    """Remove refs quebradas do LLM, injeta visualizações e embute PNGs no Markdown."""
    artifacts_dir = artifacts_dir.resolve()
    content = strip_unresolvable_image_refs(content, assets_dir=artifacts_dir)
    if visualizations:
        content = append_visualizations_to_markdown(content, visualizations)
    content = embed_markdown_images(
        content,
        markdown_dir=artifacts_dir,
        assets_dir=artifacts_dir,
    )
    # Garantia: se ainda não há PNG embutido, reinjeta e re-embuta.
    if visualizations and embedded_image_count(content) == 0:
        content = append_visualizations_to_markdown(content, visualizations)
        content = embed_markdown_images(
            content,
            markdown_dir=artifacts_dir,
            assets_dir=artifacts_dir,
        )
    return content
