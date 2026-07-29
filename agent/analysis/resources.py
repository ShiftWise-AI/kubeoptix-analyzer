"""Mapeamento de CPU e memória (requests/limits) por aplicação."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.yaml_util import (
    app_label,
    format_cpu_m,
    format_mem_mi,
    load_yaml_docs,
    meta_name,
    parse_cpu,
    parse_memory_mi,
)


@dataclass
class ContainerResources:
    app: str
    workload: str
    kind: str
    container: str
    replicas: int
    cpu_req_m: float | None
    cpu_lim_m: float | None
    mem_req_mi: float | None
    mem_lim_mi: float | None


@dataclass
class AppResourceSummary:
    app: str
    containers: int = 0
    replicas_total: int = 0
    cpu_req_m: float = 0.0
    cpu_lim_m: float = 0.0
    mem_req_mi: float = 0.0
    mem_lim_mi: float = 0.0
    missing_requests: int = 0
    missing_limits: int = 0


@dataclass
class ResourceAnalysis:
    items: list[ContainerResources] = field(default_factory=list)
    by_app: dict[str, AppResourceSummary] = field(default_factory=dict)
    ns_cpu_req_m: float = 0.0
    ns_cpu_lim_m: float = 0.0
    ns_mem_req_mi: float = 0.0
    ns_mem_lim_mi: float = 0.0


def _containers_from_workload(doc: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    spec = doc.get("spec") or {}
    replicas = int(spec.get("replicas") or 1)
    template_spec = ((spec.get("template") or {}).get("spec")) or {}
    containers = list(template_spec.get("containers") or [])
    return replicas, containers


def analyze_resources(ns: NamespaceArtifacts) -> ResourceAnalysis:
    result = ResourceAnalysis()
    for path in ns.deployments:
        for doc in load_yaml_docs(path):
            kind = doc.get("kind") or "Deployment"
            name = meta_name(doc)
            app = app_label(doc, name)
            replicas, containers = _containers_from_workload(doc)
            for c in containers:
                res = c.get("resources") or {}
                req = res.get("requests") or {}
                lim = res.get("limits") or {}
                item = ContainerResources(
                    app=app,
                    workload=name,
                    kind=str(kind),
                    container=str(c.get("name") or "container"),
                    replicas=replicas,
                    cpu_req_m=parse_cpu(req.get("cpu")),
                    cpu_lim_m=parse_cpu(lim.get("cpu")),
                    mem_req_mi=parse_memory_mi(req.get("memory")),
                    mem_lim_mi=parse_memory_mi(lim.get("memory")),
                )
                result.items.append(item)

                summary = result.by_app.setdefault(app, AppResourceSummary(app=app))
                summary.containers += 1
                summary.replicas_total += replicas
                if item.cpu_req_m is None:
                    summary.missing_requests += 1
                else:
                    summary.cpu_req_m += item.cpu_req_m * replicas
                if item.cpu_lim_m is None:
                    summary.missing_limits += 1
                else:
                    summary.cpu_lim_m += item.cpu_lim_m * replicas
                if item.mem_req_mi is None:
                    summary.missing_requests += 1
                else:
                    summary.mem_req_mi += item.mem_req_mi * replicas
                if item.mem_lim_mi is None:
                    summary.missing_limits += 1
                else:
                    summary.mem_lim_mi += item.mem_lim_mi * replicas

    for summary in result.by_app.values():
        result.ns_cpu_req_m += summary.cpu_req_m
        result.ns_cpu_lim_m += summary.cpu_lim_m
        result.ns_mem_req_mi += summary.mem_req_mi
        result.ns_mem_lim_mi += summary.mem_lim_mi

    return result


def render_resources_md(ns_name: str, analysis: ResourceAnalysis) -> str:
    lines = [
        f"# Recursos de CPU e memória — `{ns_name}`",
        "",
        "Valores extraídos de `resources.requests` (mínimo) e `resources.limits` (máximo) "
        "nos workloads, multiplicados pelas réplicas configuradas.",
        "",
        "## Sumário do namespace",
        "",
        f"- **CPU requests (mín.):** {format_cpu_m(analysis.ns_cpu_req_m)} cores-equivalentes "
        f"({analysis.ns_cpu_req_m:.0f}m)",
        f"- **CPU limits (máx.):** {format_cpu_m(analysis.ns_cpu_lim_m)} "
        f"({analysis.ns_cpu_lim_m:.0f}m)",
        f"- **Memória requests (mín.):** {format_mem_mi(analysis.ns_mem_req_mi)}",
        f"- **Memória limits (máx.):** {format_mem_mi(analysis.ns_mem_lim_mi)}",
        "",
        "## Por aplicação",
        "",
        "| Aplicação | Contêineres | Réplicas* | CPU req | CPU lim | Mem req | Mem lim | Sem req | Sem lim |",
        "|-----------|-------------|-----------|---------|---------|---------|---------|---------|---------|",
    ]
    for app in sorted(analysis.by_app):
        s = analysis.by_app[app]
        lines.append(
            f"| `{app}` | {s.containers} | {s.replicas_total} | "
            f"{format_cpu_m(s.cpu_req_m)} | {format_cpu_m(s.cpu_lim_m)} | "
            f"{format_mem_mi(s.mem_req_mi)} | {format_mem_mi(s.mem_lim_mi)} | "
            f"{s.missing_requests} | {s.missing_limits} |"
        )
    if not analysis.by_app:
        lines.append("| — | — | — | — | — | — | — | — | — |")

    lines.extend(
        [
            "",
            "Nota: a coluna de réplicas soma réplicas por contêiner/workload "
            "(não necessariamente pods únicos).",
            "",
            "## Detalhamento por contêiner",
            "",
            "| App | Workload | Kind | Contêiner | Réplicas | CPU req | CPU lim | Mem req | Mem lim |",
            "|-----|----------|------|-----------|----------|---------|---------|---------|---------|",
        ]
    )
    for item in sorted(analysis.items, key=lambda i: (i.app, i.workload, i.container)):
        lines.append(
            f"| `{item.app}` | `{item.workload}` | {item.kind} | `{item.container}` | "
            f"{item.replicas} | {format_cpu_m(item.cpu_req_m)} | {format_cpu_m(item.cpu_lim_m)} | "
            f"{format_mem_mi(item.mem_req_mi)} | {format_mem_mi(item.mem_lim_mi)} |"
        )
    if not analysis.items:
        lines.append("| — | — | — | — | — | — | — | — | — |")

    # Gráficos pizza — distribuição de limites no namespace
    mem_counter: dict[str, int] = {
        app: int(round(s.mem_lim_mi))
        for app, s in analysis.by_app.items()
        if s.mem_lim_mi > 0
    }
    cpu_counter: dict[str, int] = {
        app: int(round(s.cpu_lim_m))
        for app, s in analysis.by_app.items()
        if s.cpu_lim_m > 0
    }

    def _pie(title: str, data: dict[str, int]) -> list[str]:
        out = ["```mermaid", "pie showData", f"    title {title}"]
        if not data:
            out.append('    "sem dados" : 1')
        else:
            for label, value in sorted(data.items(), key=lambda x: -x[1])[:12]:
                safe = str(label).replace('"', "'")
                out.append(f'    "{safe}" : {value}')
        out.append("```")
        return out

    lines.extend(["", "## Gráfico pizza — memória limits por aplicação (Mi)", ""])
    lines.extend(_pie("Memoria limits Mi por aplicacao", mem_counter))
    lines.extend(["", "## Gráfico pizza — CPU limits por aplicação (millicores)", ""])
    lines.extend(_pie("CPU limits m por aplicacao", cpu_counter))
    lines.append("")
    return "\n".join(lines)
