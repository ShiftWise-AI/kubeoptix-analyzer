"""Modelos de dados para gráficos e diagramas do relatório."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PieSlice:
    label: str
    value: float


@dataclass(frozen=True)
class CompositionDataset:
    title: str
    slices: tuple[PieSlice, ...]


@dataclass(frozen=True)
class DiagramNode:
    id: str
    node_type: str
    label: str
    subgraph: str | None = None


@dataclass(frozen=True)
class DiagramEdge:
    source_id: str
    target_id: str
    edge_type: str
    label: str | None = None


@dataclass(frozen=True)
class FlowchartSubgraph:
    id: str
    title: str


@dataclass(frozen=True)
class FlowchartDataset:
    title: str
    direction: Literal["LR", "TB"] = "TB"
    nodes: tuple[DiagramNode, ...] = ()
    edges: tuple[DiagramEdge, ...] = ()
    subgraphs: tuple[FlowchartSubgraph, ...] = ()
