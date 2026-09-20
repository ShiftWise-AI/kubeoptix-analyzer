"""Analysis of logs, metrics, and monitoring resources."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.yaml_util import load_yaml_docs, meta_name
from agent.i18n import t

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
class Opportunity:
    text: str
    infra: bool = False


@dataclass
class ObservabilityResult:
    log_hits: list[LogHit] = field(default_factory=list)
    errors_by_app: Counter = field(default_factory=Counter)
    errors_by_category: Counter = field(default_factory=Counter)
    service_monitors: list[str] = field(default_factory=list)
    pod_monitors: list[str] = field(default_factory=list)
    prometheus_rules: list[str] = field(default_factory=list)
    apps_without_monitor: list[str] = field(default_factory=list)
    opportunities: list[Opportunity] = field(default_factory=list)
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
        result.opportunities.append(Opportunity(t("obs.no_monitors"), infra=True))
    if result.apps_without_monitor:
        shown = ", ".join(f"`{a}`" for a in result.apps_without_monitor[:20])
        suffix = "…" if len(result.apps_without_monitor) > 20 else ""
        result.opportunities.append(
            Opportunity(t("obs.apps_without", apps=shown, suffix=suffix))
        )
    if not result.prometheus_rules:
        result.opportunities.append(Opportunity(t("obs.no_rules"), infra=True))
    if result.errors_by_app:
        top = result.errors_by_app.most_common(3)
        apps = ", ".join(f"`{a}` ({n})" for a, n in top)
        result.opportunities.append(Opportunity(t("obs.top_errors", apps=apps)))
    if result.errors_by_category.get("Exception") or result.errors_by_category.get(
        "ERROR"
    ):
        result.opportunities.append(Opportunity(t("obs.structured")))
    if any("previous" in f.name for f in ns.log_files):
        result.opportunities.append(Opportunity(t("obs.previous")))
    if not result.opportunities:
        result.opportunities.append(Opportunity(t("obs.few")))
    return result


def render_observability_md(
    ns_name: str,
    obs: ObservabilityResult,
    *,
    assets=None,
) -> str:
    lines = [
        t("obs.title", name=ns_name),
        "",
        t("obs.inventory"),
        "",
        f"- ServiceMonitors: **{len(obs.service_monitors)}**"
        + (f" (`{', '.join(obs.service_monitors)}`)" if obs.service_monitors else ""),
        f"- PodMonitors: **{len(obs.pod_monitors)}**"
        + (f" (`{', '.join(obs.pod_monitors)}`)" if obs.pod_monitors else ""),
        f"- PrometheusRules: **{len(obs.prometheus_rules)}**"
        + (f" (`{', '.join(obs.prometheus_rules)}`)" if obs.prometheus_rules else ""),
        "",
        t("obs.chart_app"),
        "",
    ]
    if assets is not None:
        lines.append(
            assets.render_composition(
                f"{ns_name}_errors_by_app",
                t("viz.title_errors_app"),
                obs.errors_by_app,
                include_other=True,
            )
        )
    else:
        lines.append(t("viz.unavailable"))
    lines.extend(
        [
            "",
            t("obs.chart_cat"),
            "",
        ]
    )
    if assets is not None:
        lines.append(
            assets.render_composition(
                f"{ns_name}_errors_by_category",
                t("viz.title_errors_cat"),
                obs.errors_by_category,
                include_other=True,
            )
        )
    else:
        lines.append(t("viz.unavailable"))
    lines.extend(["", t("obs.table_title"), "", t("obs.table")])
    total_errors = sum(obs.errors_by_app.values()) or 1
    if obs.errors_by_app:
        for app, n in obs.errors_by_app.most_common():
            pct = 100.0 * n / total_errors
            lines.append(f"| `{app}` | {n} | {pct:.1f}% |")
    else:
        lines.append("| — | 0 | 0% |")

    lines.extend(["", t("obs.samples"), ""])
    if not obs.log_hits:
        lines.append(t("obs.no_patterns"))
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

    lines.extend(["", t("obs.opportunities"), ""])
    for idx, opp in enumerate(obs.opportunities, start=1):
        lines.append(f"{idx}. {opp.text}")
    lines.append("")
    return "\n".join(lines)
