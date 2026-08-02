"""Analysis of logs, metrics, and monitoring resources."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.yaml_util import load_yaml_docs, meta_name

ERROR_PATTERNS = [
    ("ERROR", re.compile(r"\bERROR\b|\bError\b")),
    ("Exception", re.compile(r"Exception|Traceback")),
    ("FATAL", re.compile(r"\bFATAL\b|\bFatal\b")),
    ("OOM", re.compile(r"OutOfMemory|OOMKilled|\bOOM\b")),
    ("CrashLoop", re.compile(r"CrashLoop|Back-off")),
    ("Timeout", re.compile(r"timeout|Timeout|timed out", re.IGNORECASE)),
    ("Denied", re.compile(r"\bdenied\b|\bUnauthorized\b|\bForbidden\b", re.IGNORECASE)),
]


def _app_from_log_name(filename: str) -> str:
    stem = Path(filename).name
    stem = stem.replace("-previous", "")
    if stem.endswith(".log"):
        stem = stem[:-4]
    parts = stem.split("-")
    while len(parts) > 1 and (
        re.fullmatch(r"[a-f0-9]{5,10}", parts[-1])
        or re.fullmatch(r"[a-z0-9]{5}", parts[-1])
    ):
        parts.pop()
    return "-".join(parts) if parts else stem


@dataclass
class LogHit:
    app: str
    category: str
    location: str
    snippet: str


@dataclass
class ObservabilityResult:
    log_hits: list[LogHit] = field(default_factory=list)
    errors_by_app: Counter = field(default_factory=Counter)
    errors_by_category: Counter = field(default_factory=Counter)
    service_monitors: list[str] = field(default_factory=list)
    pod_monitors: list[str] = field(default_factory=list)
    prometheus_rules: list[str] = field(default_factory=list)
    apps_without_monitor: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    sample_limit: int = 100


def analyze_observability(
    ns: NamespaceArtifacts,
    apps: list[str],
) -> ObservabilityResult:
    result = ObservabilityResult()

    for path in ns.service_monitors:
        for doc in load_yaml_docs(path):
            result.service_monitors.append(meta_name(doc) or path.stem)
    for path in ns.pod_monitors:
        for doc in load_yaml_docs(path):
            result.pod_monitors.append(meta_name(doc) or path.stem)
    for path in ns.prometheus_rules:
        for doc in load_yaml_docs(path):
            result.prometheus_rules.append(meta_name(doc) or path.stem)

    monitored = set(result.service_monitors) | set(result.pod_monitors)
    result.apps_without_monitor = sorted(a for a in apps if a not in monitored)

    for log_file in ns.log_files:
        app = _app_from_log_name(log_file.name)
        try:
            text = log_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = log_file.name
        for lineno, line in enumerate(text.splitlines(), start=1):
            for category, regex in ERROR_PATTERNS:
                if regex.search(line):
                    result.errors_by_app[app] += 1
                    result.errors_by_category[category] += 1
                    if len(result.log_hits) < result.sample_limit:
                        snippet = line.strip()
                        if len(snippet) > 220:
                            snippet = snippet[:220] + "..."
                        result.log_hits.append(
                            LogHit(app, category, f"{rel}:{lineno}", snippet)
                        )
                    break

    if not result.service_monitors and not result.pod_monitors:
        result.opportunities.append(
            "Não há ServiceMonitor/PodMonitor no namespace — oportunidade de "
            "expor métricas via Prometheus Operator para SLIs/SLOs."
        )
    if result.apps_without_monitor:
        result.opportunities.append(
            "Aplicações sem monitor dedicado: "
            + ", ".join(f"`{a}`" for a in result.apps_without_monitor[:20])
            + ("…" if len(result.apps_without_monitor) > 20 else "")
            + "."
        )
    if not result.prometheus_rules:
        result.opportunities.append(
            "Ausência de PrometheusRule — criar alertas para taxa de erro, "
            "latência e reinícios de pod."
        )
    if result.errors_by_app:
        top = result.errors_by_app.most_common(3)
        result.opportunities.append(
            "Concentrar correção de erros nas aplicações com mais ocorrências: "
            + ", ".join(f"`{a}` ({n})" for a, n in top)
            + "."
        )
    if result.errors_by_category.get("Exception") or result.errors_by_category.get(
        "ERROR"
    ):
        result.opportunities.append(
            "Padronizar logging estruturado (JSON) com `trace_id`/`correlation_id` "
            "para melhorar rastreabilidade operacional entre serviços."
        )
    if any("previous" in f.name for f in ns.log_files):
        result.opportunities.append(
            "Há logs `-previous` (pods reiniciados) — investigar causas de "
            "reinício (OOM, falhas de probe, crashes) e correlacionar com eventos."
        )
    if not result.opportunities:
        result.opportunities.append(
            "Poucos sinais de gap de observabilidade nos artefatos; validar "
            "dashboards e runbooks no ambiente de operação."
        )
    return result


def _mermaid_pie(title: str, data: Counter, limit: int = 10) -> str:
    """Mermaid pie chart for errors or other quantitative distributions."""
    items = data.most_common(limit)
    lines = ["```mermaid", "pie showData", f"    title {title}"]
    if not items:
        lines.append('    "sem dados" : 1')
        lines.append("```")
        return "\n".join(lines)

    total_all = sum(data.values())
    shown = sum(v for _, v in items)
    for label, value in items:
        safe = str(label).replace('"', "'")
        lines.append(f'    "{safe}" : {value}')
    if total_all > shown:
        lines.append(f'    "outros" : {total_all - shown}')
    lines.append("```")
    return "\n".join(lines)


def render_observability_md(ns_name: str, obs: ObservabilityResult) -> str:
    lines = [
        f"# Observabilidade — logs, métricas e monitoramento — `{ns_name}`",
        "",
        "## Inventário de monitoramento",
        "",
        f"- ServiceMonitors: **{len(obs.service_monitors)}**"
        + (f" (`{', '.join(obs.service_monitors)}`)" if obs.service_monitors else ""),
        f"- PodMonitors: **{len(obs.pod_monitors)}**"
        + (f" (`{', '.join(obs.pod_monitors)}`)" if obs.pod_monitors else ""),
        f"- PrometheusRules: **{len(obs.prometheus_rules)}**"
        + (f" (`{', '.join(obs.prometheus_rules)}`)" if obs.prometheus_rules else ""),
        "",
        "## Gráfico pizza — erros por aplicação/sistema",
        "",
        _mermaid_pie("Erros por aplicacao", obs.errors_by_app),
        "",
        "## Gráfico pizza — erros por categoria",
        "",
        _mermaid_pie("Erros por categoria", obs.errors_by_category),
        "",
        "## Tabela quantitativa por aplicação",
        "",
        "| Aplicação | Ocorrências | % do total |",
        "|-----------|-------------|------------|",
    ]
    total_errors = sum(obs.errors_by_app.values()) or 1
    if obs.errors_by_app:
        for app, n in obs.errors_by_app.most_common():
            pct = 100.0 * n / total_errors
            lines.append(f"| `{app}` | {n} | {pct:.1f}% |")
    else:
        lines.append("| — | 0 | 0% |")

    lines.extend(["", "## Amostra de evidências em logs", ""])
    if not obs.log_hits:
        lines.append("Nenhum padrão de erro encontrado nos logs coletados.")
        lines.append("")
    else:
        by_app: dict[str, list[LogHit]] = defaultdict(list)
        for hit in obs.log_hits:
            by_app[hit.app].append(hit)
        for app in sorted(by_app):
            lines.append(f"### `{app}`")
            lines.append("")
            for hit in by_app[app][:8]:
                lines.append(
                    f"- **{hit.category}** `{hit.location}` — `{hit.snippet}`"
                )
            lines.append("")

    lines.extend(["## Oportunidades de melhoria (rastreabilidade e correção)", ""])
    for idx, opp in enumerate(obs.opportunities, start=1):
        lines.append(f"{idx}. {opp}")
    lines.append("")
    return "\n".join(lines)
