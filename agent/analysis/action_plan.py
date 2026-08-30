"""Action plan separated by infrastructure versus application."""

from __future__ import annotations

from agent.analysis.configmaps_security import ConfigMapSecurityResult
from agent.analysis.findings import FindingsResult
from agent.analysis.observability import ObservabilityResult
from agent.analysis.resources import ResourceAnalysis


def render_action_plan_md(
    ns_name: str,
    findings: FindingsResult,
    resources: ResourceAnalysis,
    obs: ObservabilityResult,
    configmaps: ConfigMapSecurityResult,
) -> str:
    infra: list[str] = []
    apps: list[str] = []

    for f in findings.items:
        bullet = f"- **[{f.severity.upper()}]** {f.title} — {f.detail}"
        if f.area == "infraestrutura":
            infra.append(bullet)
        else:
            apps.append(bullet)

    if resources.ns_cpu_lim_m and any(
        s.missing_limits or s.missing_requests for s in resources.by_app.values()
    ):
        infra.append(
            "- Review the namespace quota/LimitRange and standardize requests/limits "
            "across all workloads."
        )

    missing_req = [
        s.app for s in resources.by_app.values() if s.missing_requests or s.missing_limits
    ]
    if missing_req:
        infra.append(
            "- Complete requests/limits in the applications: "
            + ", ".join(f"`{a}`" for a in sorted(set(missing_req))[:15])
            + "."
        )

    for opp in obs.opportunities:
        text = f"- {opp}"
        if any(
            k in opp.lower()
            for k in (
                "servicemonitor",
                "podmonitor",
                "prometheus",
                "alerta",
                "métricas",
                "metricas",
                "namespace",
            )
        ):
            infra.append(text)
        else:
            apps.append(text)

    for rec in configmaps.recommendations:
        apps.append(f"- {rec}")

    # Dedup preservando ordem
    def uniq(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for i in items:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out

    infra = uniq(infra)
    apps = uniq(apps)

    lines = [
        f"# Action plan — `{ns_name}`",
        "",
        "Derived from the assessment reports (findings, resources, observability, "
        "and ConfigMaps). Split by responsibility.",
        "",
        "## 1. Cluster / platform infrastructure actions",
        "",
    ]
    if infra:
        lines.extend(infra)
    else:
        lines.append("- No priority infrastructure action was identified automatically.")
    lines.extend(["", "## 2. Application improvement actions", ""])
    if apps:
        lines.extend(apps)
    else:
        lines.append("- No priority application action was identified automatically.")

    lines.extend(
        [
            "",
            "## 3. Suggested prioritization",
            "",
            "1. **HIGH** severity items (TLS, limits, probes, secrets).",
            "2. Observability (monitors, alerts, structured logging).",
            "3. **MEDIUM/LOW** items (liveness, replicas, image tags).",
            "",
            "## 4. Acceptance criteria",
            "",
            "- Critical Routes with TLS and without insecure HTTP when applicable.",
            "- 100% of workloads with defined requests and limits.",
            "- Critical applications with readiness/liveness checks and ≥2 replicas or HPA.",
            "- Secrets removed from ConfigMaps; ConfigMaps used only for non-sensitive configuration.",
            "- Basic metrics and alerts covering error rate and restarts.",
            "",
        ]
    )
    return "\n".join(lines)
