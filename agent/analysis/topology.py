"""Reverse architecture inferred from Deployments, Services, Routes, and ConfigMaps."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.yaml_util import (
    app_label,
    extract_service_refs_from_text,
    load_yaml_docs,
    meta_name,
)
from agent.i18n import t, yn


@dataclass
class Edge:
    source: str
    target: str
    kind: str


@dataclass
class TopologyResult:
    apps: list[str] = field(default_factory=list)
    routes: list[dict[str, str]] = field(default_factory=list)
    services: list[dict[str, str]] = field(default_factory=list)
    http_deps: list[tuple[str, str]] = field(default_factory=list)  # app -> app
    config_refs: list[tuple[str, str]] = field(default_factory=list)  # app -> configmap/secret
    edges: list[Edge] = field(default_factory=list)
    human_summary: list[str] = field(default_factory=list)


def analyze_topology(ns: NamespaceArtifacts) -> TopologyResult:
    result = TopologyResult()
    deploy_by_label: dict[str, str] = {}
    service_to_app: dict[str, str] = {}

    for path in ns.deployments:
        for doc in load_yaml_docs(path):
            name = meta_name(doc)
            app = app_label(doc, name)
            labels = ((doc.get("spec") or {}).get("selector") or {}).get(
                "matchLabels"
            ) or {}
            app_sel = str(labels.get("app") or app)
            deploy_by_label[app_sel] = app
            result.apps.append(app)

            containers = (
                ((doc.get("spec") or {}).get("template") or {}).get("spec") or {}
            ).get("containers") or []
            for c in containers:
                for ref in c.get("envFrom") or []:
                    if "configMapRef" in ref:
                        cm = (ref.get("configMapRef") or {}).get("name")
                        if cm:
                            result.config_refs.append((app, f"ConfigMap:{cm}"))
                    if "secretRef" in ref:
                        sec = (ref.get("secretRef") or {}).get("name")
                        if sec:
                            result.config_refs.append((app, f"Secret:{sec}"))

    for path in ns.services:
        for doc in load_yaml_docs(path):
            name = meta_name(doc)
            app = app_label(doc, name)
            selector = (doc.get("spec") or {}).get("selector") or {}
            target = deploy_by_label.get(str(selector.get("app") or ""), app)
            service_to_app[name] = target or app
            result.services.append(
                {"name": name, "app": app, "target": target or app}
            )

    for path in ns.routes:
        for doc in load_yaml_docs(path):
            name = meta_name(doc)
            host = str(((doc.get("spec") or {}).get("host")) or t("route.no_host"))
            to = str(((doc.get("spec") or {}).get("to") or {}).get("name") or "")
            tls = bool((doc.get("spec") or {}).get("tls"))
            target_app = service_to_app.get(to, to)
            result.routes.append(
                {
                    "name": name,
                    "host": host,
                    "service": to,
                    "app": target_app,
                    "tls": "yes" if tls else "no",
                }
            )

    for path in ns.configmaps:
        text = path.read_text(encoding="utf-8", errors="replace")
        for doc in load_yaml_docs(path):
            cm_name = meta_name(doc)
            cm_app = app_label(doc, cm_name)
            data = doc.get("data") or {}
            blob = "\n".join(f"{k}={v}" for k, v in data.items())
            refs = extract_service_refs_from_text(blob) | extract_service_refs_from_text(
                text
            )
            for svc in refs:
                target = service_to_app.get(svc, svc)
                if cm_app and target and cm_app != target:
                    result.http_deps.append((cm_app, target))

    result.apps = sorted(set(result.apps))
    result.http_deps = sorted(set(result.http_deps))
    result.config_refs = sorted(set(result.config_refs))

    # Legacy-style textual edges.
    for r in result.routes:
        if r.get("app"):
            result.edges.append(Edge(f"user via {r['host']}", r["app"], "HTTP entry"))
    for src, dst in result.http_deps:
        result.edges.append(Edge(src, dst, "calls"))

    result.human_summary = _human_summary(result)
    return result


def _human_summary(topo: TopologyResult) -> list[str]:
    lines: list[str] = []
    if topo.routes:
        lines.append(t("topo.entry_title"))
        for r in topo.routes:
            tls = t("topo.with_tls") if r["tls"] == "yes" else t("topo.without_tls")
            lines.append(
                t("topo.entry_line", host=r["host"], tls=tls, app=r["app"])
            )
    else:
        lines.append(t("topo.no_route"))

    if topo.http_deps:
        lines.append("")
        lines.append(t("topo.calls_title"))
        for src, dst in topo.http_deps:
            lines.append(t("topo.call_line", src=src, dst=dst))
    else:
        lines.append("")
        lines.append(t("topo.no_calls"))

    if topo.config_refs:
        lines.append("")
        lines.append(t("topo.config_title"))
        by_app: dict[str, list[str]] = {}
        for app, ref in topo.config_refs:
            by_app.setdefault(app, []).append(ref)
        for app in sorted(by_app):
            refs = ", ".join(f"`{r}`" for r in sorted(set(by_app[app])))
            lines.append(t("topo.config_line", app=app, refs=refs))
    return lines


def render_topology_md(
    ns_name: str,
    topo: TopologyResult,
    *,
    ns: NamespaceArtifacts | None = None,
    assets=None,
) -> str:
    lines = [
        t("topo.title", name=ns_name),
        "",
        t("topo.intro"),
        "",
        t("topo.brief"),
        "",
    ]
    lines.extend(topo.human_summary or [t("topo.fallback")])
    lines.extend(["", t("topo.diagram"), ""])
    if assets is not None and ns is not None:
        diagram_md, _engine = assets.render_topology(
            f"{ns_name}_topology",
            t("viz.title_architecture", namespace=ns_name),
            ns,
            topo,
        )
        lines.append(diagram_md)
    else:
        lines.append(t("diagram.unavailable"))
    lines.extend(
        [
            "",
            t("topo.routes"),
            "",
            t("topo.routes_header"),
        ]
    )
    for r in topo.routes:
        tls = yn(r["tls"] == "yes")
        lines.append(f"| `{r['host']}` | **{r['app']}** | {tls} |")
    if not topo.routes:
        lines.append("| — | — | — |")

    lines.extend(
        [
            "",
            t("topo.apps"),
            "",
        ]
    )
    if topo.apps:
        for app in topo.apps:
            svc = next((s["name"] for s in topo.services if s["target"] == app), "—")
            lines.append(t("topo.app_line", app=app, service=svc))
    else:
        lines.append(t("topo.no_apps"))
    lines.append("")
    return "\n".join(lines)
