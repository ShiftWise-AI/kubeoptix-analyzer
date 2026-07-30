"""Mapeamento de CPU/memória e sugestões conservadoras (resources + HPA)."""

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

# Baselines conservadoras quando faltam requests/limits (valores por contêiner).
DEFAULT_CPU_REQ_M = 100.0
DEFAULT_CPU_LIM_M = 250.0
DEFAULT_MEM_REQ_MI = 128.0
DEFAULT_MEM_LIM_MI = 256.0
# Limite tipicamente 2x o request (Burstable conservador).
LIMIT_TO_REQUEST_RATIO = 2.0
# Se limit/request > isto, sugerir apertar o limit.
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
    # Sugestões por contêiner (já arredondadas)
    sug_cpu_req_m: float = 0.0
    sug_cpu_lim_m: float = 0.0
    sug_mem_req_mi: float = 0.0
    sug_mem_lim_mi: float = 0.0
    suggestion_notes: list[str] = field(default_factory=list)


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
    # Por pod (soma dos contêineres do workload principal)
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
    ns_cpu_req_m: float = 0.0
    ns_cpu_lim_m: float = 0.0
    ns_mem_req_mi: float = 0.0
    ns_mem_lim_mi: float = 0.0
    ns_sug_cpu_req_m: float = 0.0
    ns_sug_cpu_lim_m: float = 0.0
    ns_sug_mem_req_mi: float = 0.0
    ns_sug_mem_lim_mi: float = 0.0


def _round_cpu_m(value: float) -> float:
    """Arredonda millicores para valores práticos."""
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
    """Sugestão conservadora de (request, limit) para um recurso."""
    notes: list[str] = []
    if req is None and lim is None:
        notes.append(f"{kind}: ausentes — baseline conservadora {default_req}/{default_lim}")
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
        notes.append(f"{kind}: só limit definido — request sugerido ≈ 50% do limit")
        return sug_req, sug_lim, notes

    if lim is None and req is not None:
        if kind == "CPU":
            sug_req = _round_cpu_m(req)
            sug_lim = _round_cpu_m(req * LIMIT_TO_REQUEST_RATIO)
        else:
            sug_req = _round_mem_mi(req)
            sug_lim = _round_mem_mi(req * LIMIT_TO_REQUEST_RATIO)
        notes.append(f"{kind}: só request definido — limit sugerido ≈ 2× request")
        return sug_req, sug_lim, notes

    assert req is not None and lim is not None
    if lim < req:
        if kind == "CPU":
            sug_req = _round_cpu_m(req)
            sug_lim = _round_cpu_m(req * LIMIT_TO_REQUEST_RATIO)
        else:
            sug_req = _round_mem_mi(req)
            sug_lim = _round_mem_mi(req * LIMIT_TO_REQUEST_RATIO)
        notes.append(f"{kind}: limit < request — corrigido para limit ≈ 2× request")
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
            f"{kind}: burst alto (limit/request={ratio:.1f}) — "
            f"sugerido apertar limit para ≈ {LIMIT_TO_REQUEST_RATIO:.0f}× request"
        )
        return sug_req, sug_lim, notes

    if abs(lim - req) < 1e-6:
        if kind == "CPU":
            sug_lim = _round_cpu_m(lim)
            sug_req = _round_cpu_m(lim * 0.7)
        else:
            sug_lim = _round_mem_mi(lim)
            sug_req = _round_mem_mi(lim * 0.7)
        notes.append(
            f"{kind}: Guaranteed (req=lim) — sugerido Burstable com request ≈ 70% do limit"
        )
        return sug_req, sug_lim, notes

    # Já razoável: manter, só arredondar
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


def analyze_resources(ns: NamespaceArtifacts) -> ResourceAnalysis:
    result = ResourceAnalysis()
    result.hpas = _parse_hpas(ns)

    # Primeiro passo: itens por contêiner + sugestões
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
                    sug_cpu_req_m=sug_cpu_req,
                    sug_cpu_lim_m=sug_cpu_lim,
                    sug_mem_req_mi=sug_mem_req,
                    sug_mem_lim_mi=sug_mem_lim,
                    suggestion_notes=notes_cpu + notes_mem,
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
        # Sugestão de namespace: por pod × réplicas sugeridas mínimas (conservador)
        min_r = max(2, summary.replicas) if summary.replicas < 2 else summary.replicas
        result.ns_sug_cpu_req_m += summary.sug_cpu_req_m * min_r
        result.ns_sug_cpu_lim_m += summary.sug_cpu_lim_m * min_r
        result.ns_sug_mem_req_mi += summary.sug_mem_req_mi * min_r
        result.ns_sug_mem_lim_mi += summary.sug_mem_lim_mi * min_r

        # HPA conservador
        min_replicas = max(2, summary.replicas)
        max_replicas = max(min_replicas + 2, min_replicas * 2)
        # Cap conservador: não sugerir mais que 6 sem evidência de carga
        max_replicas = min(max_replicas, 6)
        rationale_parts = [
            f"minReplicas={min_replicas} (HA: evitar réplica única)",
            f"maxReplicas={max_replicas} (escala moderada, teto conservador)",
            "targetCPUUtilization=70% (margem antes do throttling)",
        ]
        if existing:
            rationale_parts.append(
                f"Já existe HPA `{existing.name}` "
                f"(min={existing.min_replicas}, max={existing.max_replicas}) — revisar valores."
            )
        else:
            rationale_parts.append("Nenhum HPA encontrado para este workload.")

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


def render_resources_md(ns_name: str, analysis: ResourceAnalysis) -> str:
    lines = [
        f"# Recursos de CPU e memória — `{ns_name}`",
        "",
        "Valores atuais extraídos de `resources.requests` (mínimo reservado) e "
        "`resources.limits` (teto). Sugestões abaixo são **conservadoras**: priorizam "
        "estabilidade (Burstable com limit ≈ 2× request), HA (≥2 réplicas) e escala "
        "moderada via HPA — sem assumir métricas reais de uso (VPA/Prometheus).",
        "",
        "## Sumário do namespace (atual)",
        "",
        f"- **CPU requests:** {format_cpu_m(analysis.ns_cpu_req_m)} ({analysis.ns_cpu_req_m:.0f}m)",
        f"- **CPU limits:** {format_cpu_m(analysis.ns_cpu_lim_m)} ({analysis.ns_cpu_lim_m:.0f}m)",
        f"- **Memória requests:** {format_mem_mi(analysis.ns_mem_req_mi)}",
        f"- **Memória limits:** {format_mem_mi(analysis.ns_mem_lim_mi)}",
        "",
        "## Sumário sugerido (conservador, namespace)",
        "",
        f"- **CPU requests sugeridos:** {format_cpu_m(analysis.ns_sug_cpu_req_m)} "
        f"({analysis.ns_sug_cpu_req_m:.0f}m)",
        f"- **CPU limits sugeridos:** {format_cpu_m(analysis.ns_sug_cpu_lim_m)} "
        f"({analysis.ns_sug_cpu_lim_m:.0f}m)",
        f"- **Memória requests sugerida:** {format_mem_mi(analysis.ns_sug_mem_req_mi)}",
        f"- **Memória limits sugerida:** {format_mem_mi(analysis.ns_sug_mem_lim_mi)}",
        "",
        "_Estimativa com réplicas mínimas sugeridas (≥2 quando hoje há 1). "
        "Validar com métricas reais antes de aplicar em produção._",
        "",
        "## Por aplicação (atual)",
        "",
        "| Aplicação | Contêineres | Réplicas | CPU req | CPU lim | Mem req | Mem lim | Sem req | Sem lim | HPA |",
        "|-----------|-------------|----------|---------|---------|---------|---------|---------|---------|-----|",
    ]
    for app in sorted(analysis.by_app):
        s = analysis.by_app[app]
        lines.append(
            f"| `{app}` | {s.containers} | {s.replicas} | "
            f"{format_cpu_m(s.cpu_req_m)} | {format_cpu_m(s.cpu_lim_m)} | "
            f"{format_mem_mi(s.mem_req_mi)} | {format_mem_mi(s.mem_lim_mi)} | "
            f"{s.missing_requests} | {s.missing_limits} | "
            f"{'sim' if s.has_hpa else 'não'} |"
        )
    if not analysis.by_app:
        lines.append("| — | — | — | — | — | — | — | — | — | — |")

    lines.extend(
        [
            "",
            "## Sugestão conservadora por contêiner",
            "",
            "| App | Workload | Contêiner | CPU req→sug | CPU lim→sug | Mem req→sug | Mem lim→sug | Notas |",
            "|-----|----------|-----------|-------------|-------------|-------------|-------------|-------|",
        ]
    )
    for item in sorted(analysis.items, key=lambda i: (i.app, i.workload, i.container)):
        notes = "; ".join(item.suggestion_notes) if item.suggestion_notes else "manter faixa atual (arredondada)"
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

    # Exemplo YAML de resources (primeiro item com notas, senão o primeiro)
    example_item = next(
        (i for i in analysis.items if i.suggestion_notes),
        analysis.items[0] if analysis.items else None,
    )
    if example_item:
        lines.extend(
            [
                "",
                f"## Exemplo YAML — resources sugeridos (`{example_item.workload}` / `{example_item.container}`)",
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
            "## Sugestões de HPA (conservadoras)",
            "",
            "| App | Workload | min | max | CPU alvo | Mem alvo | Situação |",
            "|-----|----------|-----|-----|----------|----------|----------|",
        ]
    )
    for sug in sorted(analysis.hpa_suggestions, key=lambda s: s.app):
        situ = f"existe `{sug.existing_hpa}`" if sug.existing_hpa else "criar"
        lines.append(
            f"| `{sug.app}` | `{sug.workload}` | {sug.min_replicas} | {sug.max_replicas} | "
            f"{sug.target_cpu}% | {sug.target_memory}% | {situ} |"
        )
    if not analysis.hpa_suggestions:
        lines.append("| — | — | — | — | — | — | — |")

    if analysis.hpa_suggestions:
        # Escolhe um exemplo representativo (sem HPA se possível)
        sug_ex = next(
            (s for s in analysis.hpa_suggestions if not s.existing_hpa),
            analysis.hpa_suggestions[0],
        )
        lines.extend(
            [
                "",
                f"### Racional ({sug_ex.app})",
                "",
                sug_ex.rationale,
                "",
                f"## Exemplo YAML — HPA sugerido (`{sug_ex.workload}-hpa`)",
                "",
                "```yaml",
                _yaml_hpa_example(ns_name, sug_ex).rstrip(),
                "```",
                "",
                "Notas de aplicação:",
                "",
                "- Aplicar HPA apenas em workloads stateless (Deployments); StatefulSets exigem cuidado.",
                "- `behavior.scaleDown` com janela de 300s reduz flapping.",
                "- Confirmar que metrics-server (ou monitoramento equivalente) está saudável no cluster.",
                "- Após aplicar, observar 1–2 ciclos de carga antes de reduzir `maxReplicas` ou apertar targets.",
                "",
            ]
        )

    # Gráficos pizza
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

    lines.extend(["## Gráfico pizza — memória limits atuais por aplicação (Mi)", ""])
    lines.extend(_pie("Memoria limits Mi por aplicacao", mem_counter))
    lines.extend(["", "## Gráfico pizza — CPU limits atuais por aplicação (millicores)", ""])
    lines.extend(_pie("CPU limits m por aplicacao", cpu_counter))
    lines.append("")
    return "\n".join(lines)
