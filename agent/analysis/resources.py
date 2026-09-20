"""CPU/memory mapping and conservative recommendations (resources + HPA)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.worknodes import WorknodeCapacity
from agent.analysis.yaml_util import (
    app_label,
    format_cpu_m,
    format_mem_mi,
    load_yaml_docs,
    meta_name,
    parse_cpu,
    parse_memory_mi,
)
from agent.i18n import t, yn

# Conservative baselines when requests/limits are missing (per-container values).
DEFAULT_CPU_REQ_M = 100.0
DEFAULT_CPU_LIM_M = 250.0
DEFAULT_MEM_REQ_MI = 128.0
DEFAULT_MEM_LIM_MI = 256.0
# Limit is typically 2x the request (conservative Burstable profile).
LIMIT_TO_REQUEST_RATIO = 2.0
# If limit/request is above this ratio, recommend tightening the limit.
MAX_BURST_RATIO = 3.0


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
    qos_class: str = "BestEffort"
    # Per-container suggestions (already rounded).
    sug_cpu_req_m: float = 0.0
    sug_cpu_lim_m: float = 0.0
    sug_mem_req_mi: float = 0.0
    sug_mem_lim_mi: float = 0.0
    suggestion_notes: list[str] = field(default_factory=list)
    has_affinity: bool = False
    has_pod_anti_affinity: bool = False
    has_pod_affinity: bool = False
    has_node_affinity: bool = False


@dataclass
class AffinityInventory:
    workload: str
    kind: str
    app: str
    has_node_affinity: bool = False
    has_pod_affinity: bool = False
    has_pod_anti_affinity: bool = False


def qos_class_for_container(
    cpu_req: float | None,
    cpu_lim: float | None,
    mem_req: float | None,
    mem_lim: float | None,
) -> str:
    """Approximate per-container QoS using the same rule as a single-container pod."""
    has_any_req = cpu_req is not None or mem_req is not None
    has_any_lim = cpu_lim is not None or mem_lim is not None
    if not has_any_req and not has_any_lim:
        return "BestEffort"
    cpu_guaranteed = (
        cpu_req is not None
        and cpu_lim is not None
        and abs(cpu_req - cpu_lim) < 1e-6
    )
    mem_guaranteed = (
        mem_req is not None
        and mem_lim is not None
        and abs(mem_req - mem_lim) < 1e-6
    )
    if (
        cpu_req is not None
        and cpu_lim is not None
        and mem_req is not None
        and mem_lim is not None
        and cpu_guaranteed
        and mem_guaranteed
    ):
        return "Guaranteed"
    return "Burstable"


def _affinity_flags(template_spec: dict[str, Any]) -> tuple[bool, bool, bool]:
    affinity = template_spec.get("affinity") or {}
    if not isinstance(affinity, dict):
        return False, False, False
    return (
        bool(affinity.get("nodeAffinity")),
        bool(affinity.get("podAffinity")),
        bool(affinity.get("podAntiAffinity")),
    )


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
    # Per pod (sum of containers in the main workload)
    sug_cpu_req_m: float = 0.0
    sug_cpu_lim_m: float = 0.0
    sug_mem_req_mi: float = 0.0
    sug_mem_lim_mi: float = 0.0
    workload_name: str = ""
    workload_kind: str = "Deployment"
    replicas: int = 1
    has_hpa: bool = False


@dataclass
class HpaInfo:
    name: str
    target: str
    min_replicas: int | None
    max_replicas: int | None


@dataclass
class HpaSuggestion:
    app: str
    workload: str
    workload_kind: str
    min_replicas: int
    max_replicas: int
    target_cpu: int
    target_memory: int | None
    rationale: str
    existing_hpa: str | None = None


@dataclass
class ResourceAnalysis:
    items: list[ContainerResources] = field(default_factory=list)
    by_app: dict[str, AppResourceSummary] = field(default_factory=dict)
    hpas: list[HpaInfo] = field(default_factory=list)
    hpa_suggestions: list[HpaSuggestion] = field(default_factory=list)
    affinities: list[AffinityInventory] = field(default_factory=list)
    worknodes: WorknodeCapacity | None = None
    ns_cpu_req_m: float = 0.0
    ns_cpu_lim_m: float = 0.0
    ns_mem_req_mi: float = 0.0
    ns_mem_lim_mi: float = 0.0
    ns_sug_cpu_req_m: float = 0.0
    ns_sug_cpu_lim_m: float = 0.0
    ns_sug_mem_req_mi: float = 0.0
    ns_sug_mem_lim_mi: float = 0.0


def _round_cpu_m(value: float) -> float:
    """Round millicores to practical values."""
    if value < 50:
        return 50.0
    if value < 200:
        return float(int(round(value / 25.0) * 25))
    if value < 1000:
        return float(int(round(value / 50.0) * 50))
    return float(int(round(value / 100.0) * 100))


def _round_mem_mi(value: float) -> float:
    if value < 64:
        return 64.0
    if value < 512:
        return float(int(round(value / 32.0) * 32))
    if value < 2048:
        return float(int(round(value / 64.0) * 64))
    return float(int(round(value / 128.0) * 128))


def _suggest_pair(
    req: float | None,
    lim: float | None,
    default_req: float,
    default_lim: float,
    kind: str,
) -> tuple[float, float, list[str]]:
    """Conservative suggestion for a resource (request, limit) pair."""
    notes: list[str] = []
    label = t("kind.cpu") if kind == "CPU" else t("kind.memory")
    if req is None and lim is None:
        notes.append(t("suggest.missing", kind=label, req=default_req, lim=default_lim))
        return default_req, default_lim, notes

    if req is None and lim is not None:
        sug_req = _round_cpu_m(lim / LIMIT_TO_REQUEST_RATIO) if kind == "CPU" else _round_mem_mi(
            lim / LIMIT_TO_REQUEST_RATIO
        )
        sug_lim = lim if kind == "CPU" else lim
        if kind == "CPU":
            sug_lim = _round_cpu_m(lim)
            sug_req = _round_cpu_m(lim / LIMIT_TO_REQUEST_RATIO)
        else:
            sug_lim = _round_mem_mi(lim)
            sug_req = _round_mem_mi(lim / LIMIT_TO_REQUEST_RATIO)
        notes.append(t("suggest.limit_only", kind=label))
        return sug_req, sug_lim, notes

    if lim is None and req is not None:
        if kind == "CPU":
            sug_req = _round_cpu_m(req)
            sug_lim = _round_cpu_m(req * LIMIT_TO_REQUEST_RATIO)
        else:
            sug_req = _round_mem_mi(req)
            sug_lim = _round_mem_mi(req * LIMIT_TO_REQUEST_RATIO)
        notes.append(t("suggest.request_only", kind=label))
        return sug_req, sug_lim, notes

    assert req is not None and lim is not None
    if lim < req:
        if kind == "CPU":
            sug_req = _round_cpu_m(req)
            sug_lim = _round_cpu_m(req * LIMIT_TO_REQUEST_RATIO)
        else:
            sug_req = _round_mem_mi(req)
            sug_lim = _round_mem_mi(req * LIMIT_TO_REQUEST_RATIO)
        notes.append(t("suggest.limit_lt_request", kind=label))
        return sug_req, sug_lim, notes

    ratio = lim / req if req > 0 else LIMIT_TO_REQUEST_RATIO
    if ratio > MAX_BURST_RATIO:
        if kind == "CPU":
            sug_req = _round_cpu_m(req)
            sug_lim = _round_cpu_m(req * LIMIT_TO_REQUEST_RATIO)
        else:
            sug_req = _round_mem_mi(req)
            sug_lim = _round_mem_mi(req * LIMIT_TO_REQUEST_RATIO)
        notes.append(
            t(
                "suggest.burst",
                kind=label,
                ratio=f"{ratio:.1f}",
                factor=f"{LIMIT_TO_REQUEST_RATIO:.0f}",
            )
        )
        return sug_req, sug_lim, notes

    if abs(lim - req) < 1e-6:
        if kind == "CPU":
            sug_lim = _round_cpu_m(lim)
            sug_req = _round_cpu_m(lim * 0.7)
        else:
            sug_lim = _round_mem_mi(lim)
            sug_req = _round_mem_mi(lim * 0.7)
        notes.append(t("suggest.guaranteed", kind=label))
        return sug_req, sug_lim, notes

    # Already reasonable: keep as-is, only round.
    if kind == "CPU":
        return _round_cpu_m(req), _round_cpu_m(lim), notes
    return _round_mem_mi(req), _round_mem_mi(lim), notes


def _containers_from_workload(doc: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    spec = doc.get("spec") or {}
    replicas = int(spec.get("replicas") or 1)
    template_spec = ((spec.get("template") or {}).get("spec")) or {}
    containers = list(template_spec.get("containers") or [])
    return replicas, containers


def _parse_hpas(ns: NamespaceArtifacts) -> list[HpaInfo]:
    infos: list[HpaInfo] = []
    for path in ns.hpas:
        for doc in load_yaml_docs(path):
            spec = doc.get("spec") or {}
            target = ((spec.get("scaleTargetRef") or {}).get("name")) or ""
            infos.append(
                HpaInfo(
                    name=meta_name(doc) or path.stem,
                    target=str(target),
                    min_replicas=spec.get("minReplicas"),
                    max_replicas=spec.get("maxReplicas"),
                )
            )
    return infos


def _hpa_for_app(hpas: list[HpaInfo], app: str, workload: str) -> HpaInfo | None:
    for h in hpas:
        if h.target in {app, workload} or h.name in {app, f"{app}-hpa", workload}:
            return h
    return None


def analyze_resources(
    ns: NamespaceArtifacts,
    worknodes: WorknodeCapacity | None = None,
) -> ResourceAnalysis:
    result = ResourceAnalysis(worknodes=worknodes)
    result.hpas = _parse_hpas(ns)

    # First pass: per-container items + recommendations.
    for path in ns.deployments:
        for doc in load_yaml_docs(path):
            kind = doc.get("kind") or "Deployment"
            name = meta_name(doc)
            app = app_label(doc, name)
            replicas, containers = _containers_from_workload(doc)
            template_spec = (
                ((doc.get("spec") or {}).get("template") or {}).get("spec")
            ) or {}
            node_aff, pod_aff, pod_anti = _affinity_flags(template_spec)
            result.affinities.append(
                AffinityInventory(
                    workload=name,
                    kind=str(kind),
                    app=app,
                    has_node_affinity=node_aff,
                    has_pod_affinity=pod_aff,
                    has_pod_anti_affinity=pod_anti,
                )
            )
            for c in containers:
                res = c.get("resources") or {}
                req = res.get("requests") or {}
                lim = res.get("limits") or {}
                cpu_req = parse_cpu(req.get("cpu"))
                cpu_lim = parse_cpu(lim.get("cpu"))
                mem_req = parse_memory_mi(req.get("memory"))
                mem_lim = parse_memory_mi(lim.get("memory"))

                sug_cpu_req, sug_cpu_lim, notes_cpu = _suggest_pair(
                    cpu_req, cpu_lim, DEFAULT_CPU_REQ_M, DEFAULT_CPU_LIM_M, "CPU"
                )
                sug_mem_req, sug_mem_lim, notes_mem = _suggest_pair(
                    mem_req, mem_lim, DEFAULT_MEM_REQ_MI, DEFAULT_MEM_LIM_MI, "Mem"
                )

                item = ContainerResources(
                    app=app,
                    workload=name,
                    kind=str(kind),
                    container=str(c.get("name") or "container"),
                    replicas=replicas,
                    cpu_req_m=cpu_req,
                    cpu_lim_m=cpu_lim,
                    mem_req_mi=mem_req,
                    mem_lim_mi=mem_lim,
                    qos_class=qos_class_for_container(
                        cpu_req, cpu_lim, mem_req, mem_lim
                    ),
                    sug_cpu_req_m=sug_cpu_req,
                    sug_cpu_lim_m=sug_cpu_lim,
                    sug_mem_req_mi=sug_mem_req,
                    sug_mem_lim_mi=sug_mem_lim,
                    suggestion_notes=notes_cpu + notes_mem,
                    has_affinity=node_aff or pod_aff or pod_anti,
                    has_pod_anti_affinity=pod_anti,
                    has_pod_affinity=pod_aff,
                    has_node_affinity=node_aff,
                )
                result.items.append(item)

                summary = result.by_app.setdefault(app, AppResourceSummary(app=app))
                summary.containers += 1
                summary.replicas_total += replicas
                summary.workload_name = name
                summary.workload_kind = str(kind)
                summary.replicas = replicas
                summary.sug_cpu_req_m += sug_cpu_req
                summary.sug_cpu_lim_m += sug_cpu_lim
                summary.sug_mem_req_mi += sug_mem_req
                summary.sug_mem_lim_mi += sug_mem_lim
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
        existing = _hpa_for_app(result.hpas, summary.app, summary.workload_name)
        summary.has_hpa = existing is not None
        result.ns_cpu_req_m += summary.cpu_req_m
        result.ns_cpu_lim_m += summary.cpu_lim_m
        result.ns_mem_req_mi += summary.mem_req_mi
        result.ns_mem_lim_mi += summary.mem_lim_mi
        # Namespace-level suggestion: per pod × minimum recommended replicas (conservative).
        min_r = max(2, summary.replicas) if summary.replicas < 2 else summary.replicas
        result.ns_sug_cpu_req_m += summary.sug_cpu_req_m * min_r
        result.ns_sug_cpu_lim_m += summary.sug_cpu_lim_m * min_r
        result.ns_sug_mem_req_mi += summary.sug_mem_req_mi * min_r
        result.ns_sug_mem_lim_mi += summary.sug_mem_lim_mi * min_r

        # Conservative HPA suggestion.
        min_replicas = max(2, summary.replicas)
        max_replicas = max(min_replicas + 2, min_replicas * 2)
        # Conservative cap: do not suggest more than 6 without load evidence.
        max_replicas = min(max_replicas, 6)
        rationale_parts = [
            t("hpa.reason_min", min_replicas=min_replicas),
            t("hpa.reason_max", max_replicas=max_replicas),
            t("hpa.reason_cpu"),
        ]
        if existing:
            rationale_parts.append(
                t(
                    "hpa.reason_exists",
                    name=existing.name,
                    min_replicas=existing.min_replicas,
                    max_replicas=existing.max_replicas,
                )
            )
        else:
            rationale_parts.append(t("hpa.reason_none"))

        result.hpa_suggestions.append(
            HpaSuggestion(
                app=summary.app,
                workload=summary.workload_name or summary.app,
                workload_kind=summary.workload_kind,
                min_replicas=min_replicas,
                max_replicas=max_replicas,
                target_cpu=70,
                target_memory=80,
                rationale="; ".join(rationale_parts),
                existing_hpa=existing.name if existing else None,
            )
        )

    return result


def _yaml_resources_snippet(item: ContainerResources) -> str:
    def cpu_yaml(m: float) -> str:
        if m >= 1000 and abs(m % 1000) < 1e-6:
            return str(int(m / 1000))
        return f"{int(m)}m"

    def mem_yaml(mi: float) -> str:
        if mi >= 1024 and abs(mi % 1024) < 1e-6:
            return f"{int(mi / 1024)}Gi"
        return f"{int(mi)}Mi"

    return (
        f"        resources:\n"
        f"          requests:\n"
        f"            cpu: {cpu_yaml(item.sug_cpu_req_m)}\n"
        f"            memory: {mem_yaml(item.sug_mem_req_mi)}\n"
        f"          limits:\n"
        f"            cpu: {cpu_yaml(item.sug_cpu_lim_m)}\n"
        f"            memory: {mem_yaml(item.sug_mem_lim_mi)}\n"
    )


def _yaml_hpa_example(ns_name: str, sug: HpaSuggestion) -> str:
    api_version = (
        "apps.openshift.io/v1"
        if sug.workload_kind == "DeploymentConfig"
        else "apps/v1"
    )
    kind = sug.workload_kind if sug.workload_kind in {
        "Deployment",
        "DeploymentConfig",
        "StatefulSet",
    } else "Deployment"
    if kind == "DeploymentConfig":
        api_version = "apps.openshift.io/v1"
    elif kind == "StatefulSet":
        api_version = "apps/v1"
    else:
        api_version = "apps/v1"
        kind = "Deployment"

    return f"""apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {sug.workload}-hpa
  namespace: {ns_name}
  labels:
    app: {sug.app}
spec:
  scaleTargetRef:
    apiVersion: {api_version}
    kind: {kind}
    name: {sug.workload}
  minReplicas: {sug.min_replicas}
  maxReplicas: {sug.max_replicas}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {sug.target_cpu}
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: {sug.target_memory}
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 25
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
"""


def _pct(part: float, whole: float) -> str:
    if whole <= 0:
        return "—"
    return f"{100.0 * part / whole:.1f}%"


def _render_worknode_capacity_section(ns_name: str, analysis: ResourceAnalysis) -> list[str]:
    wn = analysis.worknodes
    lines: list[str] = [
        t("wn.title"),
        "",
    ]
    if wn is None or not wn.nodes:
        lines.extend([t("wn.missing"), ""])
        return lines

    lines.extend(
        [
            t("wn.source", path=wn.source_dir),
            "",
            t("wn.header"),
            "|------|-----------------|---------------------|--------------|------------------|",
        ]
    )
    for n in wn.nodes:
        lines.append(
            f"| `{n.name}` | {format_cpu_m(n.cpu_alloc_m)} ({n.cpu_alloc_m:.0f}m) | "
            f"{format_mem_mi(n.mem_alloc_mi)} | {format_cpu_m(n.cpu_cap_m)} | "
            f"{format_mem_mi(n.mem_cap_mi)} |"
        )
    lines.append(
        f"| **{t('table.total')}** | **{format_cpu_m(wn.total_cpu_alloc_m)}** "
        f"(**{wn.total_cpu_alloc_m:.0f}m**) | "
        f"**{format_mem_mi(wn.total_mem_alloc_mi)}** | "
        f"**{format_cpu_m(wn.total_cpu_cap_m)}** | "
        f"**{format_mem_mi(wn.total_mem_cap_mi)}** |"
    )
    lines.extend(
        [
            "",
            t("wn.legend_title"),
            "",
            t("wn.legend_alloc"),
            t("wn.legend_cap"),
            t("wn.legend_use"),
            "",
        ]
    )

    avail_cpu = wn.total_cpu_alloc_m
    avail_mem = wn.total_mem_alloc_mi
    req_cpu, lim_cpu = analysis.ns_cpu_req_m, analysis.ns_cpu_lim_m
    req_mem, lim_mem = analysis.ns_mem_req_mi, analysis.ns_mem_lim_mi
    sug_req_cpu, sug_lim_cpu = analysis.ns_sug_cpu_req_m, analysis.ns_sug_cpu_lim_m
    sug_req_mem, sug_lim_mem = analysis.ns_sug_mem_req_mi, analysis.ns_sug_mem_lim_mi

    lines.extend(
        [
            t("cmp.title", name=ns_name),
            "",
            t("cmp.h1"),
            "",
            t("cmp.t1"),
            f"| {t('kind.cpu')} | {format_cpu_m(avail_cpu)} | {format_cpu_m(req_cpu)} | "
            f"{_pct(req_cpu, avail_cpu)} |",
            f"| {t('kind.memory')} | {format_mem_mi(avail_mem)} | {format_mem_mi(req_mem)} | "
            f"{_pct(req_mem, avail_mem)} |",
            "",
            t("cmp.h2"),
            "",
            t("cmp.t2"),
            f"| {t('kind.cpu')} | {format_cpu_m(avail_cpu)} | {format_cpu_m(lim_cpu)} | "
            f"{_pct(lim_cpu, avail_cpu)} |",
            f"| {t('kind.memory')} | {format_mem_mi(avail_mem)} | {format_mem_mi(lim_mem)} | "
            f"{_pct(lim_mem, avail_mem)} |",
            "",
            t("cmp.h3"),
            "",
            t("cmp.t3"),
            f"| {t('kind.cpu')} | {format_cpu_m(avail_cpu)} | {format_cpu_m(sug_req_cpu)} | "
            f"{format_cpu_m(sug_lim_cpu)} | {_pct(sug_req_cpu, avail_cpu)} | "
            f"{_pct(sug_lim_cpu, avail_cpu)} |",
            f"| {t('kind.memory')} | {format_mem_mi(avail_mem)} | {format_mem_mi(sug_req_mem)} | "
            f"{format_mem_mi(sug_lim_mem)} | {_pct(sug_req_mem, avail_mem)} | "
            f"{_pct(sug_lim_mem, avail_mem)} |",
            "",
            t("eco.title"),
            "",
            t("eco.intro"),
            "",
        ]
    )

    eco_cpu_req = req_cpu - sug_req_cpu
    eco_cpu_lim = lim_cpu - sug_lim_cpu
    eco_mem_req = req_mem - sug_req_mem
    eco_mem_lim = lim_mem - sug_lim_mem

    def _eco_cell(delta: float, base: float, kind: str) -> str:
        """delta > 0 means savings; delta < 0 means an increase (for example: HA)."""
        if kind == "cpu":
            val = format_cpu_m(abs(delta))
        else:
            val = format_mem_mi(abs(delta))
        pct = _pct(abs(delta), base) if base else "—"
        if delta > 0:
            return f"↓ {val} ({pct})"
        if delta < 0:
            return f"↑ {val} ({pct})"
        return f"0 ({pct})"

    lines.extend(
        [
            t("eco.header"),
            f"| {t('eco.req_row')} | {_eco_cell(eco_cpu_req, req_cpu, 'cpu')} | "
            f"{_eco_cell(eco_mem_req, req_mem, 'mem')} |",
            f"| {t('eco.lim_row')} | {_eco_cell(eco_cpu_lim, lim_cpu, 'cpu')} | "
            f"{_eco_cell(eco_mem_lim, lim_mem, 'mem')} |",
            "",
            t("eco.reading"),
            "",
            t("eco.down"),
            t("eco.up"),
            t(
                "eco.requests_line",
                cpu=_eco_cell(eco_cpu_req, req_cpu, "cpu"),
                mem=_eco_cell(eco_mem_req, req_mem, "mem"),
            ),
            t(
                "eco.limits_line",
                cpu=_eco_cell(eco_cpu_lim, lim_cpu, "cpu"),
                mem=_eco_cell(eco_mem_lim, lim_mem, "mem"),
            ),
            t(
                "eco.today",
                cpu_req=_pct(req_cpu, avail_cpu),
                mem_req=_pct(req_mem, avail_mem),
                cpu_lim=_pct(lim_cpu, avail_cpu),
                mem_lim=_pct(lim_mem, avail_mem),
            ),
            t(
                "eco.opt",
                cpu_req=_pct(sug_req_cpu, avail_cpu),
                mem_req=_pct(sug_req_mem, avail_mem),
                cpu_lim=_pct(sug_lim_cpu, avail_cpu),
                mem_lim=_pct(sug_lim_mem, avail_mem),
            ),
            "",
            t("eco.note"),
            "",
        ]
    )
    return lines


def render_resources_md(
    ns_name: str,
    analysis: ResourceAnalysis,
    *,
    assets=None,
) -> str:
    lines = [
        t("res.title", name=ns_name),
        "",
        t("res.intro"),
        "",
        t("res.current"),
        "",
        t(
            "res.cpu_req",
            value=format_cpu_m(analysis.ns_cpu_req_m),
            raw=f"{analysis.ns_cpu_req_m:.0f}",
        ),
        t(
            "res.cpu_lim",
            value=format_cpu_m(analysis.ns_cpu_lim_m),
            raw=f"{analysis.ns_cpu_lim_m:.0f}",
        ),
        t("res.mem_req", value=format_mem_mi(analysis.ns_mem_req_mi)),
        t("res.mem_lim", value=format_mem_mi(analysis.ns_mem_lim_mi)),
        "",
        t("res.suggested"),
        "",
        t(
            "res.cpu_req_sug",
            value=format_cpu_m(analysis.ns_sug_cpu_req_m),
            raw=f"{analysis.ns_sug_cpu_req_m:.0f}",
        ),
        t(
            "res.cpu_lim_sug",
            value=format_cpu_m(analysis.ns_sug_cpu_lim_m),
            raw=f"{analysis.ns_sug_cpu_lim_m:.0f}",
        ),
        t("res.mem_req_sug", value=format_mem_mi(analysis.ns_sug_mem_req_mi)),
        t("res.mem_lim_sug", value=format_mem_mi(analysis.ns_sug_mem_lim_mi)),
        "",
        t("res.estimate"),
        "",
    ]
    lines.extend(_render_worknode_capacity_section(ns_name, analysis))
    lines.extend(
        [
            t("res.by_app"),
            "",
            t("res.by_app_header"),
        ]
    )
    if analysis.items:
        for item in sorted(
            analysis.items, key=lambda i: (i.app, i.workload, i.container)
        ):
            summary = analysis.by_app.get(item.app)
            hpa = yn(bool(summary and summary.has_hpa))
            lines.append(
                f"| `{item.app}` | `{item.container}` | {item.replicas} | "
                f"{format_cpu_m(item.cpu_req_m)} | {format_cpu_m(item.cpu_lim_m)} | "
                f"{format_mem_mi(item.mem_req_mi)} | {format_mem_mi(item.mem_lim_mi)} | "
                f"{item.qos_class} | {hpa} |"
            )
    else:
        lines.append("| — | — | — | — | — | — | — | — | — |")

    lines.extend(
        [
            "",
            t("qos.title"),
            "",
            t("qos.guaranteed"),
            t("qos.burstable"),
            t("qos.besteffort"),
            "",
            t("qos.note"),
            "",
            t("res.suggest_title"),
            "",
            t("res.suggest_header"),
        ]
    )
    for item in sorted(analysis.items, key=lambda i: (i.app, i.workload, i.container)):
        notes = "; ".join(item.suggestion_notes) if item.suggestion_notes else t("suggest.keep")
        notes = notes.replace("|", "/")
        lines.append(
            f"| `{item.app}` | `{item.workload}` | `{item.container}` | "
            f"{format_cpu_m(item.cpu_req_m)}→**{format_cpu_m(item.sug_cpu_req_m)}** | "
            f"{format_cpu_m(item.cpu_lim_m)}→**{format_cpu_m(item.sug_cpu_lim_m)}** | "
            f"{format_mem_mi(item.mem_req_mi)}→**{format_mem_mi(item.sug_mem_req_mi)}** | "
            f"{format_mem_mi(item.mem_lim_mi)}→**{format_mem_mi(item.sug_mem_lim_mi)}** | "
            f"{notes} |"
        )
    if not analysis.items:
        lines.append("| — | — | — | — | — | — | — | — |")

    # Example resources YAML (first item with notes, otherwise the first item).
    example_item = next(
        (i for i in analysis.items if i.suggestion_notes),
        analysis.items[0] if analysis.items else None,
    )
    if example_item:
        lines.extend(
            [
                "",
                t("res.yaml_title", workload=example_item.workload, container=example_item.container),
                "",
                "```yaml",
                _yaml_resources_snippet(example_item).rstrip(),
                "```",
                "",
            ]
        )

    # HPA
    lines.extend(
        [
            t("hpa.title"),
            "",
            t("hpa.header"),
        ]
    )
    for sug in sorted(analysis.hpa_suggestions, key=lambda s: s.app):
        situ = (
            t("hpa.exists", name=sug.existing_hpa)
            if sug.existing_hpa
            else t("hpa.create")
        )
        lines.append(
            f"| `{sug.app}` | `{sug.workload}` | {sug.min_replicas} | {sug.max_replicas} | "
            f"{sug.target_cpu}% | {sug.target_memory}% | {situ} |"
        )
    if not analysis.hpa_suggestions:
        lines.append("| — | — | — | — | — | — | — |")

    if analysis.hpa_suggestions:
        # Choose a representative example (prefer one without an HPA).
        sug_ex = next(
            (s for s in analysis.hpa_suggestions if not s.existing_hpa),
            analysis.hpa_suggestions[0],
        )
        lines.extend(
            [
                "",
                t("hpa.rationale", app=sug_ex.app),
                "",
                sug_ex.rationale,
                "",
                t("hpa.yaml_title", name=f"{sug_ex.workload}-hpa"),
                "",
                "```yaml",
                _yaml_hpa_example(ns_name, sug_ex).rstrip(),
                "```",
                "",
                t("hpa.notes_title"),
                "",
                t("hpa.note1"),
                t("hpa.note2"),
                t("hpa.note3"),
                t("hpa.note4"),
                "",
            ]
        )

    # Pie charts.
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

    lines.extend([t("res.chart_mem"), ""])
    if assets is not None:
        lines.append(
            assets.render_composition(
                f"{ns_name}_mem_limits_by_app",
                t("viz.title_memory"),
                mem_counter,
            )
        )
    else:
        lines.append(t("viz.unavailable"))
    lines.extend(["", t("res.chart_cpu"), ""])
    if assets is not None:
        lines.append(
            assets.render_composition(
                f"{ns_name}_cpu_limits_by_app",
                t("viz.title_cpu"),
                cpu_counter,
            )
        )
    else:
        lines.append(t("viz.unavailable"))
    lines.extend(["", *_render_affinity_section(analysis)])
    lines.append("")
    return "\n".join(lines)


def _render_affinity_section(analysis: ResourceAnalysis) -> list[str]:
    lines = [
        t("aff.title"),
        "",
        t("aff.inventory"),
        "",
        t("aff.header"),
        "|----------|-----|--------------|-------------|-----------------|",
    ]
    if analysis.affinities:
        for aff in sorted(analysis.affinities, key=lambda a: a.workload):
            lines.append(
                f"| `{aff.workload}` | `{aff.app}` | "
                f"{yn(aff.has_node_affinity)} | "
                f"{yn(aff.has_pod_affinity)} | "
                f"{yn(aff.has_pod_anti_affinity)} |"
            )
    else:
        lines.append("| — | — | — | — | — |")

    without_anti = [
        a for a in analysis.affinities if a.has_pod_anti_affinity is False
    ]
    lines.extend(
        [
            "",
            t("aff.practices"),
            "",
            t("aff.p1"),
            t("aff.p2"),
            t("aff.p3"),
            t("aff.p4"),
            t("aff.p5"),
            t("aff.p6"),
            "",
        ]
    )
    if without_anti:
        names = ", ".join(f"`{a.workload}`" for a in without_anti[:8])
        extra = (
            t("aff.extra", count=len(without_anti) - 8) if len(without_anti) > 8 else ""
        )
        lines.extend(
            [
                t("aff.missing", names=names, extra=extra),
                "",
            ]
        )
    return lines
