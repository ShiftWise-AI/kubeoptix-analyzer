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
            "There is no ServiceMonitor/PodMonitor in the namespace — an opportunity to "
            "expose metrics through the Prometheus Operator for SLIs/SLOs."
        )
    if result.apps_without_monitor:
        result.opportunities.append(
            "Applications without a dedicated monitor: "
            + ", ".join(f"`{a}`" for a in result.apps_without_monitor[:20])
            + ("…" if len(result.apps_without_monitor) > 20 else "")
            + "."
        )
    if not result.prometheus_rules:
        result.opportunities.append(
            "No PrometheusRule is present — create alerts for error rate, latency, "
            "and pod restarts."
        )
    if result.errors_by_app:
        top = result.errors_by_app.most_common(3)
        result.opportunities.append(
            "Concentrate error remediation on applications with the highest occurrence counts: "
            + ", ".join(f"`{a}` ({n})" for a, n in top)
            + "."
        )
    if result.errors_by_category.get("Exception") or result.errors_by_category.get(
        "ERROR"
    ):
        result.opportunities.append(
            "Standardize structured logging (JSON) with `trace_id`/`correlation_id` "
            "to improve operational traceability across services."
        )
    if any("previous" in f.name for f in ns.log_files):
        result.opportunities.append(
            "There are `-previous` logs (restarted pods) — investigate restart causes "
            "(OOM, probe failures, crashes) and correlate with events."
        )
    if not result.opportunities:
        result.opportunities.append(
            "Few signs of observability gaps in the artifacts; validate dashboards and "
            "runbooks in the operating environment."
        )
    return result


def render_observability_md(
    ns_name: str,
    obs: ObservabilityResult,
    *,
    assets=None,
) -> str:
    lines = [
        f"# Observability — logs, metrics, and monitoring — `{ns_name}`",
        "",
        "## Monitoring inventory",
        "",
        f"- ServiceMonitors: **{len(obs.service_monitors)}**"
        + (f" (`{', '.join(obs.service_monitors)}`)" if obs.service_monitors else ""),
        f"- PodMonitors: **{len(obs.pod_monitors)}**"
        + (f" (`{', '.join(obs.pod_monitors)}`)" if obs.pod_monitors else ""),
        f"- PrometheusRules: **{len(obs.prometheus_rules)}**"
        + (f" (`{', '.join(obs.prometheus_rules)}`)" if obs.prometheus_rules else ""),
        "",
        "## Gráfico — erros por aplicação/sistema",
        "",
    ]
    if assets is not None:
        lines.append(
            assets.render_composition(
                f"{ns_name}_errors_by_app",
                "Erros por aplicação",
                obs.errors_by_app,
                include_other=True,
            )
        )
    else:
        lines.append("_Gráfico indisponível (assets não configurados)._")
    lines.extend(
        [
            "",
            "## Gráfico — erros por categoria",
            "",
        ]
    )
    if assets is not None:
        lines.append(
            assets.render_composition(
                f"{ns_name}_errors_by_category",
                "Erros por categoria",
                obs.errors_by_category,
                include_other=True,
            )
        )
    else:
        lines.append("_Gráfico indisponível (assets não configurados)._")
    lines.extend(
        [
            "",
            "## Quantitative table by application",
            "",
            "| Application | Occurrences | % of total |",
            "|-------------|-------------|-----------|",
        ]
    )
    total_errors = sum(obs.errors_by_app.values()) or 1
    if obs.errors_by_app:
        for app, n in obs.errors_by_app.most_common():
            pct = 100.0 * n / total_errors
            lines.append(f"| `{app}` | {n} | {pct:.1f}% |")
    else:
        lines.append("| — | 0 | 0% |")

    lines.extend(["", "## Sample log evidence", ""])
    if not obs.log_hits:
        lines.append("No error patterns were found in the collected logs.")
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

    lines.extend(["## Improvement opportunities (traceability and remediation)", ""])
    for idx, opp in enumerate(obs.opportunities, start=1):
        lines.append(f"{idx}. {opp}")
    lines.append("")
    return "\n".join(lines)
