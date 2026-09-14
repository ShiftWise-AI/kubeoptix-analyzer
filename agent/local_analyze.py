"""Orchestration of local analysis into a single pt-BR Markdown report."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from agent.analysis.action_plan import render_action_plan_md
from agent.analysis.configmaps_security import analyze_configmaps, render_configmaps_md
from agent.analysis.discovery import discover_namespaces, list_apps
from agent.analysis.findings import analyze_findings
from agent.analysis.observability import analyze_observability, render_observability_md
from agent.analysis.operators import analyze_operators, render_operators_md
from agent.analysis.references import REFERENCES_MD
from agent.analysis.resources import analyze_resources, render_resources_md
from agent.analysis.topology import analyze_topology, render_topology_md
from agent.analysis.worknodes import discover_worknodes
from agent.visualization import ReportAssets
from agent.visualization.markdown import embed_markdown_images, image_search_dirs
def resolve_report_path(
    artifacts_dir: Path,
    report_path: Path | None = None,
) -> Path:
    """Accept a .md file or a directory (writes assessment-report.md inside it)."""
    if report_path is None:
        return (artifacts_dir / "assessment-report.md").resolve()

    out = report_path.expanduser()
    if out.is_dir() or out.suffix == "":
        out = out / "assessment-report.md"
    return out.resolve()


def _demote_headings(md: str, levels: int = 1) -> str:
    """Demote Markdown headings so they fit under the single report structure."""
    prefix = "#" * levels

    def repl(match: re.Match[str]) -> str:
        hashes = match.group(1)
        rest = match.group(2)
        return f"{prefix}{hashes}{rest}"

    return re.sub(r"^(#{1,5})( .*)$", repl, md, flags=re.MULTILINE)


def _render_findings_block(ns_name: str, findings) -> str:
    lines = [
        f"### Achados de configuração — `{ns_name}`",
        "",
    ]
    if not findings.items:
        lines.append("Nenhum achado pelas heurísticas locais.")
        lines.append("")
        return "\n".join(lines)

    order = {"alto": 0, "medio": 1, "baixo": 2}
    for f in sorted(findings.items, key=lambda x: order.get(x.severity, 9)):
        loc = f" (`{f.path}`)" if f.path else ""
        lines.append(f"- **[{f.severity.upper()}]** {f.title}{loc} — {f.detail}")
    lines.append("")
    return "\n".join(lines)


def run_local_assessment(
    artifacts_dir: Path,
    report_path: Path | None = None,
) -> Path:
    artifacts_dir = artifacts_dir.resolve()
    if not artifacts_dir.is_dir():
        raise SystemExit(f"Invalid artifacts directory: {artifacts_dir}")

    out = resolve_report_path(artifacts_dir, report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    assets = ReportAssets(assets_dir=out.parent / "report_assets")

    namespaces = discover_namespaces(artifacts_dir)
    worknodes = discover_worknodes(artifacts_dir)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    parts: list[str] = [
        "# Relatório de assessment OpenShift",
        "",
        f"_Gerado em {now} (análise local, sem LLM)_",
        f"_Artefatos: `{artifacts_dir}`_",
        "",
        "## Sumário executivo",
        "",
    ]

    exec_summary: list[str] = []
    body_parts: list[str] = []

    for ns in namespaces:
        apps = list_apps(ns)
        topo = analyze_topology(ns)
        resources = analyze_resources(ns, worknodes=worknodes)
        obs = analyze_observability(ns, apps)
        cms = analyze_configmaps(ns)
        findings = analyze_findings(ns)
        operators = analyze_operators(ns)

        sev = {"alto": 0, "medio": 0, "baixo": 0}
        for f in findings.items:
            sev[f.severity] = sev.get(f.severity, 0) + 1

        exec_summary.append(
            f"- Namespace `{ns.name}`: **{len(apps)}** apps, "
            f"**{len(findings.items)}** achados "
            f"(alto={sev.get('alto', 0)}, médio={sev.get('medio', 0)}, "
            f"baixo={sev.get('baixo', 0)}), "
            f"**{sum(obs.errors_by_app.values())}** ocorrências em logs, "
            f"**{len(cms.hits)}** indícios sensíveis em ConfigMaps"
        )
        exec_summary.append(
            f"  - CPU req/lim: **{resources.ns_cpu_req_m:.0f}m** / "
            f"**{resources.ns_cpu_lim_m:.0f}m** · "
            f"Memória req/lim: **{resources.ns_mem_req_mi:.0f}Mi** / "
            f"**{resources.ns_mem_lim_mi:.0f}Mi**"
        )
        if worknodes.nodes:
            exec_summary.append(
                f"  - Workers: **{len(worknodes.nodes)}** nodes · "
                f"CPU allocatable **{worknodes.total_cpu_alloc_m:.0f}m** · "
                f"Mem allocatable **{worknodes.total_mem_alloc_mi:.0f}Mi**"
            )

        body_parts.extend(
            [
                f"## Namespace `{ns.name}`",
                "",
                "### Inventário",
                "",
                (
                    f"- Aplicações: **{len(apps)}** (`{', '.join(apps)}`)"
                    if apps
                    else "- Aplicações: **0**"
                ),
                f"- Deployments/workloads: **{len(ns.deployments)}**",
                f"- Services: **{len(ns.services)}**",
                f"- Routes: **{len(ns.routes)}**",
                f"- ConfigMaps: **{len(ns.configmaps)}**",
                f"- ClusterServiceVersions (operadores): **{len(operators.items)}**",
                f"- Arquivos de log: **{len(ns.log_files)}**",
                "",
                render_operators_md(ns.name, operators),
                _render_findings_block(ns.name, findings),
                _demote_headings(
                    render_topology_md(ns.name, topo, ns=ns, assets=assets),
                    levels=2,
                ),
                _demote_headings(
                    render_resources_md(ns.name, resources, assets=assets),
                    levels=2,
                ),
                _demote_headings(
                    render_observability_md(ns.name, obs, assets=assets),
                    levels=2,
                ),
                _demote_headings(render_configmaps_md(ns.name, cms), levels=2),
                _demote_headings(
                    render_action_plan_md(ns.name, findings, resources, obs, cms),
                    levels=2,
                ),
                "",
            ]
        )

    if not exec_summary:
        exec_summary.append("- Nenhum namespace encontrado nos artefatos.")

    parts.extend(exec_summary)
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.extend(body_parts)
    parts.append("---")
    parts.append("")
    parts.append(REFERENCES_MD.strip())
    parts.append("")

    content = "\n".join(parts)
    # Normalize repeated blank lines.
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = embed_markdown_images(
        content,
        search_dirs=image_search_dirs(artifacts_dir, out.parent),
    )
    out.write_text(content, encoding="utf-8")
    print(f"[agent] Single report written to: {out}")
    return out
