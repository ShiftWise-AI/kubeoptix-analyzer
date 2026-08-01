"""Assessment híbrido local com heurísticas, scoring e síntese por LLM local."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from openai import OpenAI

from agent.analysis.action_plan import render_action_plan_md
from agent.analysis.configmaps_security import analyze_configmaps, render_configmaps_md
from agent.analysis.discovery import NamespaceArtifacts, discover_namespaces, list_apps
from agent.analysis.findings import FindingsResult, analyze_findings
from agent.analysis.observability import (
    ERROR_PATTERNS,
    LogHit,
    ObservabilityResult,
    _app_from_log_name,
    analyze_observability,
    render_observability_md,
)
from agent.analysis.operators import analyze_operators, render_operators_md
from agent.analysis.references import REFERENCES_MD
from agent.analysis.resources import ResourceAnalysis, analyze_resources, render_resources_md
from agent.analysis.topology import analyze_topology, render_topology_md
from agent.analysis.worknodes import discover_worknodes
from agent.config import EmbeddedSettings
from agent.local_analyze import _demote_headings, _render_findings_block, resolve_report_path


@dataclass(frozen=True)
class WorkloadRisk:
    app: str
    workload: str
    kind: str
    score: int
    level: str
    reasons: list[str]


@dataclass(frozen=True)
class RankedFinding:
    title: str
    severity: str
    area: str
    detail: str
    path: str
    score: int


@dataclass(frozen=True)
class LogCluster:
    app: str
    category: str
    signature: str
    count: int
    sample: str


@dataclass(frozen=True)
class ResourceOutlier:
    app: str
    metric: str
    value: float
    median_value: float
    kind: str


@dataclass
class NamespaceEmbeddedResult:
    ns: NamespaceArtifacts
    apps: list[str]
    topology: object
    resources: ResourceAnalysis
    observability: ObservabilityResult
    configmaps: object
    findings: FindingsResult
    operators: object
    workload_risks: list[WorkloadRisk]
    prioritized_findings: list[RankedFinding]
    log_clusters: list[LogCluster]
    outliers: list[ResourceOutlier]


_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_HEX_RE = re.compile(r"\b(?:0x)?[0-9a-f]{8,}\b", re.IGNORECASE)
_NUM_RE = re.compile(r"\b\d+\b")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_SPACE_RE = re.compile(r"\s+")


def _normalize_log_line(line: str) -> str:
    text = line.strip().lower()
    text = _UUID_RE.sub("<uuid>", text)
    text = _IP_RE.sub("<ip>", text)
    text = _HEX_RE.sub("<hex>", text)
    text = re.sub(r"https?://\S+", "<url>", text)
    text = _NUM_RE.sub("<n>", text)
    text = _SPACE_RE.sub(" ", text)
    return text[:180]


def _extract_quartiles(values: list[float]) -> tuple[float, float, float]:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 0:
        lower = ordered[:mid]
        upper = ordered[mid:]
    else:
        lower = ordered[:mid]
        upper = ordered[mid + 1 :]
    q1 = median(lower) if lower else ordered[0]
    q2 = median(ordered)
    q3 = median(upper) if upper else ordered[-1]
    return float(q1), float(q2), float(q3)


def _workload_level(score: int) -> str:
    if score >= 60:
        return "alto"
    if score >= 30:
        return "medio"
    return "baixo"


def _score_workloads(
    ns: NamespaceArtifacts,
    resources: ResourceAnalysis,
    findings: FindingsResult,
    obs: ObservabilityResult,
) -> list[WorkloadRisk]:
    findings_by_path: dict[str, list] = defaultdict(list)
    for finding in findings.items:
        if finding.path:
            findings_by_path[finding.path].append(finding)

    by_workload: dict[tuple[str, str], list] = defaultdict(list)
    for item in resources.items:
        by_workload[(item.app, item.workload)].append(item)

    risks: list[WorkloadRisk] = []
    for (app, workload), items in by_workload.items():
        score = 0
        reasons: list[str] = []
        replicas = max(item.replicas for item in items)
        log_count = int(obs.errors_by_app.get(app, 0))
        score += min(30, log_count)
        if log_count:
            reasons.append(f"{log_count} ocorrencias de erro em logs")

        missing_limits = sum(
            1 for item in items if item.cpu_lim_m is None or item.mem_lim_mi is None
        )
        if missing_limits:
            score += 18
            reasons.append(f"{missing_limits} conteiner(es) sem limits completos")

        missing_requests = sum(
            1 for item in items if item.cpu_req_m is None or item.mem_req_mi is None
        )
        if missing_requests:
            score += 10
            reasons.append(f"{missing_requests} conteiner(es) sem requests completos")

        best_effort = sum(1 for item in items if item.qos_class == "BestEffort")
        if best_effort:
            score += 12
            reasons.append("QoS BestEffort detectado")

        if replicas == 1:
            score += 8
            reasons.append("replica unica")

        if not any(item.has_pod_anti_affinity for item in items) and replicas > 1:
            score += 4
            reasons.append("sem podAntiAffinity apesar de replicas > 1")

        related_findings = findings_by_path.get(f"{workload}.yaml", []) + findings_by_path.get(
            f"{workload}.yml", []
        )
        for finding in related_findings:
            if finding.severity == "alto":
                score += 16
            elif finding.severity == "medio":
                score += 8
            else:
                score += 3
            if "readinessProbe" in finding.title or "readinessProbe" in finding.detail:
                reasons.append("sem readinessProbe")
            elif "livenessProbe" in finding.title or "livenessProbe" in finding.detail:
                reasons.append("sem livenessProbe")
            elif ":latest" in finding.title or ":latest" in finding.detail:
                reasons.append("imagem mutable (:latest)")

        unique_reasons: list[str] = []
        seen: set[str] = set()
        for reason in reasons:
            if reason not in seen:
                seen.add(reason)
                unique_reasons.append(reason)

        risks.append(
            WorkloadRisk(
                app=app,
                workload=workload,
                kind=items[0].kind,
                score=min(score, 100),
                level=_workload_level(score),
                reasons=unique_reasons[:5],
            )
        )

    return sorted(risks, key=lambda risk: (-risk.score, risk.app, risk.workload))


def _rerank_findings(
    findings: FindingsResult,
    workload_risks: list[WorkloadRisk],
    obs: ObservabilityResult,
) -> list[RankedFinding]:
    risk_by_app = {risk.app: risk.score for risk in workload_risks}
    ranked: list[RankedFinding] = []
    for finding in findings.items:
        if finding.severity == "alto":
            score = 100
        elif finding.severity == "medio":
            score = 65
        else:
            score = 35

        app = ""
        if ":" in finding.title:
            app = finding.title.split(":", 1)[0].strip()
        score += min(25, int(obs.errors_by_app.get(app, 0)))
        score += risk_by_app.get(app, 0) // 3
        if "TLS" in finding.title:
            score += 12
        if "readinessProbe" in finding.title:
            score += 8
        if "resource limits" in finding.title:
            score += 10

        ranked.append(
            RankedFinding(
                title=finding.title,
                severity=finding.severity,
                area=finding.area,
                detail=finding.detail,
                path=finding.path,
                score=score,
            )
        )
    return sorted(ranked, key=lambda item: (-item.score, item.title))


def _cluster_log_errors(ns: NamespaceArtifacts, limit: int = 12) -> list[LogCluster]:
    clusters: dict[tuple[str, str, str], int] = Counter()
    samples: dict[tuple[str, str, str], str] = {}
    for log_file in ns.log_files:
        app = _app_from_log_name(log_file.name)
        try:
            text = log_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            for category, regex in ERROR_PATTERNS:
                if not regex.search(line):
                    continue
                signature = _normalize_log_line(line)
                if not signature:
                    break
                key = (app, category, signature)
                clusters[key] += 1
                samples.setdefault(key, line.strip()[:220])
                break

    result = [
        LogCluster(app=app, category=category, signature=signature, count=count, sample=samples[(app, category, signature)])
        for (app, category, signature), count in clusters.items()
    ]
    return sorted(result, key=lambda item: (-item.count, item.app, item.category))[:limit]


def _detect_resource_outliers(resources: ResourceAnalysis) -> list[ResourceOutlier]:
    metrics: dict[str, list[tuple[str, float]]] = {
        "cpu_req_m_por_pod": [],
        "cpu_lim_m_por_pod": [],
        "mem_req_mi_por_pod": [],
        "mem_lim_mi_por_pod": [],
    }
    for summary in resources.by_app.values():
        replicas = max(summary.replicas, 1)
        if summary.cpu_req_m > 0:
            metrics["cpu_req_m_por_pod"].append((summary.app, summary.cpu_req_m / replicas))
        if summary.cpu_lim_m > 0:
            metrics["cpu_lim_m_por_pod"].append((summary.app, summary.cpu_lim_m / replicas))
        if summary.mem_req_mi > 0:
            metrics["mem_req_mi_por_pod"].append((summary.app, summary.mem_req_mi / replicas))
        if summary.mem_lim_mi > 0:
            metrics["mem_lim_mi_por_pod"].append((summary.app, summary.mem_lim_mi / replicas))

    outliers: list[ResourceOutlier] = []
    for metric, pairs in metrics.items():
        if len(pairs) < 4:
            continue
        values = [value for _, value in pairs]
        q1, med, q3 = _extract_quartiles(values)
        iqr = q3 - q1
        if iqr <= 0:
            continue
        high = q3 + 1.5 * iqr
        low = max(0.0, q1 - 1.5 * iqr)
        for app, value in pairs:
            if value > high:
                outliers.append(
                    ResourceOutlier(
                        app=app,
                        metric=metric,
                        value=value,
                        median_value=med,
                        kind="alto",
                    )
                )
            elif low > 0 and value < low:
                outliers.append(
                    ResourceOutlier(
                        app=app,
                        metric=metric,
                        value=value,
                        median_value=med,
                        kind="baixo",
                    )
                )
    return sorted(outliers, key=lambda item: (item.kind != "alto", item.metric, -item.value))


def _render_workload_risks_md(ns_name: str, risks: list[WorkloadRisk]) -> str:
    lines = [
        f"# Score de risco por workload — `{ns_name}`",
        "",
        "| Aplicacao | Workload | Kind | Score | Nivel | Principais fatores |",
        "|-----------|----------|------|-------|-------|--------------------|",
    ]
    if not risks:
        lines.append("| — | — | — | 0 | baixo | sem workloads detectados |")
    else:
        for risk in risks:
            reasons = "; ".join(risk.reasons) if risk.reasons else "sem agravantes relevantes"
            lines.append(
                f"| `{risk.app}` | `{risk.workload}` | {risk.kind} | {risk.score} | "
                f"{risk.level.upper()} | {reasons} |"
            )
    lines.append("")
    return "\n".join(lines)


def _render_ranked_findings_md(ns_name: str, findings: list[RankedFinding]) -> str:
    lines = [
        f"# Achados priorizados por heuristica + reranking — `{ns_name}`",
        "",
    ]
    if not findings:
        lines.append("Nenhum achado para priorizar.")
        lines.append("")
        return "\n".join(lines)

    for idx, finding in enumerate(findings[:12], start=1):
        loc = f" (`{finding.path}`)" if finding.path else ""
        lines.append(
            f"{idx}. **[{finding.severity.upper()} | score {finding.score}]** {finding.title}{loc} — {finding.detail}"
        )
    lines.append("")
    return "\n".join(lines)


def _render_log_clusters_md(ns_name: str, clusters: list[LogCluster]) -> str:
    lines = [
        f"# Clustering de erros de log — `{ns_name}`",
        "",
        "Agrupamento por assinatura normalizada para reduzir ruido e destacar padroes repetitivos.",
        "",
        "| App | Categoria | Repeticoes | Assinatura normalizada | Exemplo |",
        "|-----|-----------|------------|------------------------|---------|",
    ]
    if not clusters:
        lines.append("| — | — | 0 | sem clusters | — |")
    else:
        for cluster in clusters:
            sample = cluster.sample.replace("|", "/")
            signature = cluster.signature.replace("|", "/")
            lines.append(
                f"| `{cluster.app}` | {cluster.category} | {cluster.count} | `{signature}` | `{sample}` |"
            )
    lines.append("")
    return "\n".join(lines)


def _render_outliers_md(ns_name: str, outliers: list[ResourceOutlier]) -> str:
    lines = [
        f"# Outliers de requests/limits — `{ns_name}`",
        "",
        "| Aplicacao | Metrica | Tipo | Valor | Mediana do grupo |",
        "|-----------|---------|------|-------|------------------|",
    ]
    if not outliers:
        lines.append("| — | — | — | — | — |")
    else:
        for outlier in outliers[:12]:
            lines.append(
                f"| `{outlier.app}` | {outlier.metric} | {outlier.kind} | {outlier.value:.1f} | {outlier.median_value:.1f} |"
            )
    lines.append("")
    return "\n".join(lines)


def _build_namespace_result(
    ns: NamespaceArtifacts,
    worknodes,
) -> NamespaceEmbeddedResult:
    apps = list_apps(ns)
    topology = analyze_topology(ns)
    resources = analyze_resources(ns, worknodes=worknodes)
    observability = analyze_observability(ns, apps)
    configmaps = analyze_configmaps(ns)
    findings = analyze_findings(ns)
    operators = analyze_operators(ns)
    workload_risks = _score_workloads(ns, resources, findings, observability)
    prioritized_findings = _rerank_findings(findings, workload_risks, observability)
    log_clusters = _cluster_log_errors(ns)
    outliers = _detect_resource_outliers(resources)
    return NamespaceEmbeddedResult(
        ns=ns,
        apps=apps,
        topology=topology,
        resources=resources,
        observability=observability,
        configmaps=configmaps,
        findings=findings,
        operators=operators,
        workload_risks=workload_risks,
        prioritized_findings=prioritized_findings,
        log_clusters=log_clusters,
        outliers=outliers,
    )


def _build_evidence_prompt(results: list[NamespaceEmbeddedResult], artifacts_dir: Path) -> str:
    lines = [
        "Diretorio de artefatos: " + str(artifacts_dir),
        "Gere uma sintese executiva curta em pt-BR usando apenas os fatos abaixo.",
        "Nao invente metricas nem recursos ausentes.",
        "",
    ]
    for result in results:
        top_risks = ", ".join(
            f"{risk.app}/{risk.workload}={risk.score}" for risk in result.workload_risks[:5]
        ) or "nenhum"
        top_findings = "; ".join(
            f"{finding.title} [score={finding.score}]" for finding in result.prioritized_findings[:5]
        ) or "nenhum"
        top_clusters = "; ".join(
            f"{cluster.app}:{cluster.category} x{cluster.count}" for cluster in result.log_clusters[:5]
        ) or "nenhum"
        outliers = "; ".join(
            f"{outlier.app}:{outlier.metric}:{outlier.kind}:{outlier.value:.1f}" for outlier in result.outliers[:5]
        ) or "nenhum"
        lines.extend(
            [
                f"Namespace: {result.ns.name}",
                f"Apps: {', '.join(result.apps) if result.apps else 'nenhuma'}",
                f"Achados: {len(result.findings.items)}",
                f"Erros em logs: {sum(result.observability.errors_by_app.values())}",
                f"Top workload risks: {top_risks}",
                f"Top findings: {top_findings}",
                f"Log clusters: {top_clusters}",
                f"Outliers: {outliers}",
                "",
            ]
        )
    lines.append(
        "Responda apenas em Markdown com as secoes: "
        "'## Sumario executivo assistido por IA', '## Prioridades de plataforma', "
        "e '## Prioridades de aplicacao'."
    )
    return "\n".join(lines)


def _generate_local_summary(settings: EmbeddedSettings, prompt: str) -> str:
    try:
        client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_s,
        )
        response = client.chat.completions.create(
            model=settings.model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Voce e um especialista em OpenShift/SRE. "
                        "Escreva em pt-BR de forma objetiva, usando apenas as evidencias fornecidas."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "Nao foi possivel usar a IA embarcada local. "
            f"Verifique o endpoint OpenAI-compatible em {settings.base_url}, "
            f"o modelo '{settings.model}' e se o runtime local esta ativo (ex.: Ollama).\n"
            f"Detalhe: {exc}"
        ) from exc

    content = response.choices[0].message.content or ""
    text = str(content).strip()
    if not text:
        raise SystemExit(
            "A IA embarcada local respondeu vazio. Verifique o modelo configurado "
            f"em EMBEDDED_MODEL ({settings.model})."
        )
    return text


def run_embedded_assessment(
    artifacts_dir: Path,
    report_path: Path | None,
    settings: EmbeddedSettings,
) -> Path:
    artifacts_dir = artifacts_dir.resolve()
    if not artifacts_dir.is_dir():
        raise SystemExit(f"Diretório de artefatos inválido: {artifacts_dir}")

    out = resolve_report_path(artifacts_dir, report_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    namespaces = discover_namespaces(artifacts_dir)
    worknodes = discover_worknodes(artifacts_dir)
    results = [_build_namespace_result(ns, worknodes) for ns in namespaces]
    summary_md = _generate_local_summary(
        settings, _build_evidence_prompt(results, artifacts_dir)
    )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts: list[str] = [
        "# Relatório de assessment OpenShift",
        "",
        f"_Gerado em {now} (modo embedded: heurísticas + {settings.model})_",
        f"_Artefatos: `{artifacts_dir}`_",
        "",
        summary_md,
        "",
        "## Sumário quantitativo",
        "",
    ]

    if not results:
        parts.append("- Nenhum namespace encontrado nos artefatos.")
        parts.append("")

    for result in results:
        sev = {"alto": 0, "medio": 0, "baixo": 0}
        for finding in result.findings.items:
            sev[finding.severity] = sev.get(finding.severity, 0) + 1
        parts.extend(
            [
                f"- Namespace `{result.ns.name}`: **{len(result.apps)}** apps, "
                f"**{len(result.findings.items)}** achados, "
                f"**{sum(result.observability.errors_by_app.values())}** ocorrencias em logs, "
                f"top workload risk **{result.workload_risks[0].app}/{result.workload_risks[0].workload}={result.workload_risks[0].score}**"
                if result.workload_risks
                else f"- Namespace `{result.ns.name}`: sem workloads para score",
                f"  - Severidade: alto={sev.get('alto', 0)}, medio={sev.get('medio', 0)}, baixo={sev.get('baixo', 0)}",
                f"  - CPU req/lim: **{result.resources.ns_cpu_req_m:.0f}m** / **{result.resources.ns_cpu_lim_m:.0f}m**",
                f"  - Mem req/lim: **{result.resources.ns_mem_req_mi:.0f}Mi** / **{result.resources.ns_mem_lim_mi:.0f}Mi**",
            ]
        )

    parts.extend(["", "---", ""])

    for result in results:
        parts.extend(
            [
                f"## Namespace `{result.ns.name}`",
                "",
                _demote_headings(_render_workload_risks_md(result.ns.name, result.workload_risks), levels=2),
                _demote_headings(_render_ranked_findings_md(result.ns.name, result.prioritized_findings), levels=2),
                _demote_headings(_render_log_clusters_md(result.ns.name, result.log_clusters), levels=2),
                _demote_headings(_render_outliers_md(result.ns.name, result.outliers), levels=2),
                render_operators_md(result.ns.name, result.operators),
                _render_findings_block(result.ns.name, result.findings),
                _demote_headings(render_topology_md(result.ns.name, result.topology), levels=2),
                _demote_headings(render_resources_md(result.ns.name, result.resources), levels=2),
                _demote_headings(render_observability_md(result.ns.name, result.observability), levels=2),
                _demote_headings(render_configmaps_md(result.ns.name, result.configmaps), levels=2),
                _demote_headings(
                    render_action_plan_md(
                        result.ns.name,
                        result.findings,
                        result.resources,
                        result.observability,
                        result.configmaps,
                    ),
                    levels=2,
                ),
                "",
            ]
        )

    parts.extend(["---", "", REFERENCES_MD.strip(), ""])
    content = "\n".join(parts)
    content = re.sub(r"\n{3,}", "\n\n", content)
    out.write_text(content, encoding="utf-8")
    print(f"[agent] Modo embedded via endpoint local: {settings.base_url}")
    print(f"[agent] Modelo embedded: {settings.model}")
    print(f"[agent] Relatório único gravado em: {out}")
    return out