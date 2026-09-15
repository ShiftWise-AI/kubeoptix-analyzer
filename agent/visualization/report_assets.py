"""Geração de PNGs e referências Markdown para o relatório."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.topology import TopologyResult
from agent.visualization.kubediagrams import is_kubediagrams_available, render_manifests
from agent.visualization.markdown import embedded_markdown_image
from agent.visualization.models import (
    CompositionDataset,
    DiagramEdge,
    DiagramNode,
    FlowchartDataset,
    PieSlice,
)
from agent.visualization.png.assets import safe_asset_filename
from agent.visualization.png.composition import render_composition_png
from agent.visualization.png.flowchart import render_flowchart_png


def _safe_id(name: str) -> str:
    cleaned = "".join(c if c.isalnum() else "_" for c in name)
    if cleaned and cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned or "node"


def collect_topology_manifests(ns: NamespaceArtifacts) -> tuple[Path, ...]:
    paths: list[Path] = []
    paths.extend(ns.deployments)
    paths.extend(ns.services)
    paths.extend(ns.routes)
    paths.extend(ns.configmaps)
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return tuple(unique)


def topology_flowchart_dataset(topo: TopologyResult, title: str) -> FlowchartDataset:
    nodes: list[DiagramNode] = []
    edges: list[DiagramEdge] = []
    declared: set[str] = set()

    def ensure_node(node_id: str, label: str, node_type: str) -> str:
        if node_id not in declared:
            declared.add(node_id)
            nodes.append(DiagramNode(id=node_id, node_type=node_type, label=label))
        return node_id

    user_id = ensure_node("usuario", "Usuário / Internet", "external")
    app_ids: dict[str, str] = {}
    for app in topo.apps:
        app_ids[app] = ensure_node(_safe_id(app), app, "workload")

    routed_apps = {r["app"] for r in topo.routes if r.get("app")}
    for app in sorted(routed_apps):
        edges.append(
            DiagramEdge(
                source_id=user_id,
                target_id=app_ids[app],
                edge_type="http",
                label="HTTP/HTTPS",
            )
        )

    for src, dst in topo.http_deps:
        edges.append(
            DiagramEdge(
                source_id=app_ids.get(src, ensure_node(_safe_id(src), src, "workload")),
                target_id=app_ids.get(dst, ensure_node(_safe_id(dst), dst, "workload")),
                edge_type="calls",
                label="calls",
            )
        )

    return FlowchartDataset(title=title, direction="TB", nodes=tuple(nodes), edges=tuple(edges))


@dataclass
class ReportAssets:
    """Pasta de imagens PNG referenciadas pelo relatório Markdown."""

    assets_dir: Path
    prefix: str = "report_assets"
    _last_diagram_engine: str | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def output_path(self, viz_id: str) -> Path:
        return self.assets_dir / safe_asset_filename(viz_id)

    def image_relpath(self, viz_id: str) -> str:
        return f"{self.prefix}/{safe_asset_filename(viz_id)}"

    def render_composition(
        self,
        viz_id: str,
        title: str,
        data: Mapping[str, int] | Counter,
        *,
        limit: int = 12,
        include_other: bool = False,
    ) -> str:
        items = sorted(data.items(), key=lambda item: -item[1])[:limit]
        if include_other and isinstance(data, Counter):
            shown = sum(value for _, value in items)
            total = sum(data.values())
            if total > shown:
                items.append(("outros", total - shown))
        if not items:
            return "_Visualização indisponível: sem dados._"

        dataset = CompositionDataset(
            title=title,
            slices=tuple(PieSlice(label=str(label), value=float(value)) for label, value in items),
        )
        output = self.output_path(viz_id)
        render_composition_png(dataset, output)
        return embedded_markdown_image(title, output)

    def render_topology(
        self,
        viz_id: str,
        title: str,
        ns: NamespaceArtifacts,
        topo: TopologyResult,
    ) -> tuple[str, str | None]:
        """Retorna bloco Markdown da imagem e engine usado (kubediagrams|matplotlib)."""
        output = self.output_path(viz_id)
        manifests = collect_topology_manifests(ns)

        if manifests and is_kubediagrams_available() and render_manifests(manifests, output):
            self._last_diagram_engine = "kubediagrams"
            lines = [
                "_Diagrama gerado a partir dos manifests YAML do namespace (KubeDiagrams)._",
                "",
                embedded_markdown_image(title, output),
            ]
            return "\n".join(lines), "kubediagrams"

        dataset = topology_flowchart_dataset(topo, title)
        render_flowchart_png(dataset, output)
        self._last_diagram_engine = "matplotlib"
        lines = [
            "_Diagrama simplificado gerado localmente (matplotlib). "
            "Para diagrama completo de arquitetura, instale `kube-diagrams` e Graphviz `dot`._",
            "",
            embedded_markdown_image(title, output),
        ]
        return "\n".join(lines), "matplotlib"
