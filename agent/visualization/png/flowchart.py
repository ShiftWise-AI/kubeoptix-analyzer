"""Diagramas de fluxo em PNG (matplotlib)."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon

from agent.visualization.chart_theme import CHART_MUTED_COLOR
from agent.visualization.models import DiagramEdge, DiagramNode, FlowchartDataset
from agent.visualization.png._mpl import save_figure
from agent.visualization.png.export_config import (
    EMPTY_CHART_FIGSIZE,
    flowchart_figsize,
    layout_profile_for_output,
)

_NODE_STYLE: dict[str, dict[str, str | float]] = {
    "external": {"facecolor": "#D6E4F0", "edgecolor": "#002F5D", "boxstyle": "round,pad=0.35"},
    "route": {"facecolor": "#F5D0CD", "edgecolor": "#C9190B"},
    "workload": {"facecolor": "#FFFFFF", "edgecolor": "#C9190B", "boxstyle": "round,pad=0.2"},
}
_DEFAULT_STYLE = {"facecolor": "#FFFFFF", "edgecolor": "#151515", "boxstyle": "round,pad=0.2"}
_EDGE_COLOR = "#4D4D4D"
_MAX_NODES_PER_COLUMN = 4


@dataclass(frozen=True)
class _NodeLayout:
    node: DiagramNode
    x: float
    y: float
    width: float
    height: float


def _estimate_size(label: str) -> tuple[float, float]:
    lines = label.split("\n")
    width = max(1.8, min(4.5, 0.12 * max(len(line) for line in lines) + 1.0))
    height = max(0.55, 0.35 * len(lines) + 0.35)
    return width, height


def _layer_nodes(nodes: tuple[DiagramNode, ...], edges: tuple[DiagramEdge, ...]) -> dict[str, int]:
    node_ids = [node.id for node in nodes]
    indegree: dict[str, int] = {node_id: 0 for node_id in node_ids}
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.source_id in indegree and edge.target_id in indegree:
            adjacency[edge.source_id].append(edge.target_id)
            indegree[edge.target_id] += 1
    layers: dict[str, int] = {}
    queue = deque(node_id for node_id, degree in indegree.items() if degree == 0)
    if not queue:
        queue = deque(node_ids[:1])
    while queue:
        current = queue.popleft()
        current_layer = layers.get(current, 0)
        for target in adjacency.get(current, []):
            layers[target] = max(layers.get(target, 0), current_layer + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    for index, node_id in enumerate(node_ids):
        layers.setdefault(node_id, index % 3)
    return layers


def _layout_group(
    nodes: tuple[DiagramNode, ...],
    edges: tuple[DiagramEdge, ...],
    *,
    start_x: float,
    direction: str,
) -> tuple[list[_NodeLayout], float, float]:
    node_ids = {node.id for node in nodes}
    local_edges = tuple(
        edge for edge in edges if edge.source_id in node_ids and edge.target_id in node_ids
    )
    layers = _layer_nodes(nodes, local_edges)
    by_layer: dict[int, list[DiagramNode]] = defaultdict(list)
    for node in nodes:
        by_layer[layers.get(node.id, 0)].append(node)

    layouts: list[_NodeLayout] = []
    layer_gap = 1.4
    row_gap = 0.35
    max_height = 0.0
    max_extent = start_x

    if direction == "TB":
        y_cursor = 0.0
        for layer_index in sorted(by_layer):
            layer_nodes = by_layer[layer_index]
            row_width = 0.0
            row_height = 0.0
            for node in layer_nodes:
                width, height = _estimate_size(node.label)
                layouts.append(
                    _NodeLayout(node=node, x=row_width, y=y_cursor, width=width, height=height)
                )
                row_width += width + row_gap
                row_height = max(row_height, height)
            max_extent = max(max_extent, row_width)
            max_height = y_cursor + row_height
            y_cursor += row_height + layer_gap
        return layouts, max_extent, max_height

    x_cursor = start_x
    group_height = 0.0
    for layer_index in sorted(by_layer):
        layer_nodes = by_layer[layer_index]
        col_x = x_cursor
        col_y = 0.0
        col_width = 0.0
        stacked = 0
        layer_height = 0.0
        for node in layer_nodes:
            width, height = _estimate_size(node.label)
            if stacked >= _MAX_NODES_PER_COLUMN:
                col_x += col_width + 0.4
                col_y = 0.0
                col_width = 0.0
                stacked = 0
            layouts.append(
                _NodeLayout(node=node, x=col_x, y=-col_y, width=width, height=height)
            )
            col_y += height + row_gap
            col_width = max(col_width, width)
            stacked += 1
            layer_height = max(layer_height, col_y)
        group_height = max(group_height, layer_height)
        x_cursor = col_x + col_width + layer_gap
    return layouts, x_cursor, group_height


def _draw_node(ax: plt.Axes, layout: _NodeLayout) -> None:
    style = dict(_DEFAULT_STYLE)
    style.update(_NODE_STYLE.get(layout.node.node_type, {}))
    x, y = layout.x, layout.y
    width, height = layout.width, layout.height
    if layout.node.node_type == "route":
        diamond = Polygon(
            [
                (x + width / 2, y),
                (x + width, y + height / 2),
                (x + width / 2, y + height),
                (x, y + height / 2),
            ],
            closed=True,
            facecolor=str(style.get("facecolor", "#F5D0CD")),
            edgecolor=str(style.get("edgecolor", "#C9190B")),
            linewidth=1.2,
        )
        ax.add_patch(diamond)
    else:
        patch = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle=str(style.get("boxstyle", "round,pad=0.2")),
            facecolor=str(style.get("facecolor", "#FFFFFF")),
            edgecolor=str(style.get("edgecolor", "#151515")),
            linewidth=1.2,
        )
        ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height / 2,
        layout.node.label,
        ha="center",
        va="center",
        fontsize=9,
        wrap=True,
    )


def _draw_edge(ax: plt.Axes, source: _NodeLayout, target: _NodeLayout, label: str | None) -> None:
    sx = source.x + source.width / 2
    sy = source.y + source.height / 2
    tx = target.x + target.width / 2
    ty = target.y + target.height / 2
    arrow = FancyArrowPatch(
        (sx, sy),
        (tx, ty),
        arrowstyle="-|>",
        mutation_scale=10,
        linewidth=1.0,
        color=_EDGE_COLOR,
        connectionstyle="arc3,rad=0.08",
    )
    ax.add_patch(arrow)
    if label:
        ax.text((sx + tx) / 2, (sy + ty) / 2, label, fontsize=6, ha="center", va="center")


def _empty_chart(output_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=EMPTY_CHART_FIGSIZE)
    ax.axis("off")
    ax.text(0.5, 0.5, "Sem dados para exibir", ha="center", va="center", fontsize=12, color=CHART_MUTED_COLOR)
    ax.set_title(title, fontsize=12, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, output_path, profile=layout_profile_for_output(output_path))
    plt.close(fig)


def render_flowchart_png(dataset: FlowchartDataset, output_path: Path) -> None:
    if not dataset.nodes:
        _empty_chart(output_path, dataset.title)
        return

    group_layouts, group_width, group_height = _layout_group(
        dataset.nodes,
        dataset.edges,
        start_x=0.5,
        direction=dataset.direction,
    )
    if not group_layouts:
        _empty_chart(output_path, dataset.title)
        return

    layout_by_id = {layout.node.id: layout for layout in group_layouts}
    fig_width, fig_height = flowchart_figsize(group_width, group_height + 2)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    for layout in group_layouts:
        _draw_node(ax, layout)
    for edge in dataset.edges:
        source = layout_by_id.get(edge.source_id)
        target = layout_by_id.get(edge.target_id)
        if source and target:
            _draw_edge(ax, source, target, edge.label)
    ax.set_title(dataset.title, fontsize=12, fontweight="bold", pad=14)
    ax.axis("off")
    ax.autoscale()
    ax.margins(0.15)
    fig.tight_layout()
    save_figure(fig, output_path, profile=layout_profile_for_output(output_path))
    plt.close(fig)
