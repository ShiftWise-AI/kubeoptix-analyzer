"""Capacidade dos worker nodes (pasta worknodes/ da coleta)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agent.analysis.yaml_util import load_yaml_docs, meta_name, parse_cpu, parse_memory_mi


@dataclass
class WorknodeInfo:
    name: str
    cpu_alloc_m: float
    mem_alloc_mi: float
    cpu_cap_m: float
    mem_cap_mi: float


@dataclass
class WorknodeCapacity:
    nodes: list[WorknodeInfo] = field(default_factory=list)
    source_dir: Path | None = None

    @property
    def total_cpu_alloc_m(self) -> float:
        return sum(n.cpu_alloc_m for n in self.nodes)

    @property
    def total_mem_alloc_mi(self) -> float:
        return sum(n.mem_alloc_mi for n in self.nodes)

    @property
    def total_cpu_cap_m(self) -> float:
        return sum(n.cpu_cap_m for n in self.nodes)

    @property
    def total_mem_cap_mi(self) -> float:
        return sum(n.mem_cap_mi for n in self.nodes)


def _find_worknodes_dir(artifacts_dir: Path) -> Path | None:
    """Procura worknodes/ na raiz dos artefatos ou no diretório pai."""
    candidates = [
        artifacts_dir / "worknodes",
        artifacts_dir.parent / "worknodes",
    ]
    for path in candidates:
        if not path.is_dir():
            continue
        files = list(path.glob("*.yaml")) + list(path.glob("*.yml"))
        if files:
            return path
    return None


def discover_worknodes(artifacts_dir: Path) -> WorknodeCapacity:
    artifacts_dir = artifacts_dir.resolve()
    wn_dir = _find_worknodes_dir(artifacts_dir)
    capacity = WorknodeCapacity(source_dir=wn_dir)
    if wn_dir is None:
        return capacity

    for path in sorted(list(wn_dir.glob("*.yaml")) + list(wn_dir.glob("*.yml"))):
        for doc in load_yaml_docs(path):
            if (doc.get("kind") or "") != "Node":
                continue
            status = doc.get("status") or {}
            alloc = status.get("allocatable") or {}
            cap = status.get("capacity") or {}
            cpu_alloc = parse_cpu(alloc.get("cpu")) or 0.0
            mem_alloc = parse_memory_mi(alloc.get("memory")) or 0.0
            cpu_cap = parse_cpu(cap.get("cpu")) or cpu_alloc
            mem_cap = parse_memory_mi(cap.get("memory")) or mem_alloc
            capacity.nodes.append(
                WorknodeInfo(
                    name=meta_name(doc) or path.stem,
                    cpu_alloc_m=cpu_alloc,
                    mem_alloc_mi=mem_alloc,
                    cpu_cap_m=cpu_cap,
                    mem_cap_mi=mem_cap,
                )
            )
    return capacity
