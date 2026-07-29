"""Plano de ação separado: infraestrutura vs aplicação."""

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
            "- Revisar Quota/LimitRange do namespace e padronizar requests/limits "
            "em todos os workloads."
        )

    missing_req = [
        s.app for s in resources.by_app.values() if s.missing_requests or s.missing_limits
    ]
    if missing_req:
        infra.append(
            "- Completar requests/limits nas aplicações: "
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
        f"# Plano de ação — `{ns_name}`",
        "",
        "Plano derivado dos relatórios de assessment (achados, recursos, "
        "observabilidade e ConfigMaps). Separado por responsabilidade.",
        "",
        "## 1. Ações de infraestrutura do cluster / plataforma",
        "",
    ]
    if infra:
        lines.extend(infra)
    else:
        lines.append("- Nenhuma ação de infraestrutura prioritária identificada automaticamente.")
    lines.extend(["", "## 2. Ações de melhoria da aplicação", ""])
    if apps:
        lines.extend(apps)
    else:
        lines.append("- Nenhuma ação de aplicação prioritária identificada automaticamente.")

    lines.extend(
        [
            "",
            "## 3. Priorização sugerida",
            "",
            "1. Itens de severidade **ALTO** (TLS, limits, probes, segredos).",
            "2. Observabilidade (monitores, alertas, logging estruturado).",
            "3. Itens **MÉDIO/BAIXO** (liveness, réplicas, tags de imagem).",
            "",
            "## 4. Critérios de aceite",
            "",
            "- Routes críticas com TLS e sem HTTP inseguro quando aplicável.",
            "- 100% dos workloads com requests e limits definidos.",
            "- Aplicações críticas com readiness/liveness e ≥2 réplicas ou HPA.",
            "- Segredos fora de ConfigMaps; ConfigMaps apenas com configuração não sensível.",
            "- Métricas e alertas básicos cobrindo taxa de erro e reinícios.",
            "",
        ]
    )
    return "\n".join(lines)
