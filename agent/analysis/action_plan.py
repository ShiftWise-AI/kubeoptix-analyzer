"""Action plan separated by infrastructure versus application."""

from __future__ import annotations

from agent.analysis.configmaps_security import ConfigMapSecurityResult
from agent.analysis.findings import FindingsResult
from agent.analysis.observability import ObservabilityResult
from agent.analysis.resources import ResourceAnalysis
from agent.i18n import severity_label, t


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
        label = severity_label(f.severity).upper()
        bullet = f"- **[{label}]** {f.title} — {f.detail}"
        if f.area == "infraestrutura":
            infra.append(bullet)
        else:
            apps.append(bullet)

    if resources.ns_cpu_lim_m and any(
        s.missing_limits or s.missing_requests for s in resources.by_app.values()
    ):
        infra.append(t("action.review_quota"))

    missing_req = [
        s.app for s in resources.by_app.values() if s.missing_requests or s.missing_limits
    ]
    if missing_req:
        infra.append(
            t(
                "action.complete_resources",
                apps=", ".join(f"`{a}`" for a in sorted(set(missing_req))[:15]),
            )
        )

    for opp in obs.opportunities:
        bullet = f"- {opp.text}"
        if opp.infra:
            infra.append(bullet)
        else:
            apps.append(bullet)

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
        t("action.title", name=ns_name),
        "",
        t("action.intro"),
        "",
        t("action.infra"),
        "",
    ]
    if infra:
        lines.extend(infra)
    else:
        lines.append(t("action.infra_none"))
    lines.extend(["", t("action.apps"), ""])
    if apps:
        lines.extend(apps)
    else:
        lines.append(t("action.apps_none"))

    lines.extend(
        [
            "",
            t("action.priority"),
            "",
            t("action.p1"),
            t("action.p2"),
            t("action.p3"),
            "",
            t("action.accept"),
            "",
            t("action.a1"),
            t("action.a2"),
            t("action.a3"),
            t("action.a4"),
            t("action.a5"),
            "",
        ]
    )
    return "\n".join(lines)
