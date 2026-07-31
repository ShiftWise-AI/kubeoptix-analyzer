"""Arquitetura reversa simples a partir de Deployments, Services, Routes e ConfigMaps."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.yaml_util import (
    app_label,
    extract_service_refs_from_text,
    load_yaml_docs,
    meta_name,
)


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
    config_refs: list[tuple[str, str]] = field(default_factory=list)  # app -> cm/secret
    edges: list[Edge] = field(default_factory=list)
    mermaid: str = ""
    human_summary: list[str] = field(default_factory=list)


def _safe_id(name: str) -> str:
    cleaned = "".join(c if c.isalnum() else "_" for c in name)
    if cleaned and cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned or "node"


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
            host = str(((doc.get("spec") or {}).get("host")) or "(sem host)")
            to = str(((doc.get("spec") or {}).get("to") or {}).get("name") or "")
            tls = bool((doc.get("spec") or {}).get("tls"))
            target_app = service_to_app.get(to, to)
            result.routes.append(
                {
                    "name": name,
                    "host": host,
                    "service": to,
                    "app": target_app,
                    "tls": "sim" if tls else "não",
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

    # edges legados (lista textual)
    for r in result.routes:
        if r.get("app"):
            result.edges.append(Edge(f"usuário via {r['host']}", r["app"], "entrada HTTP"))
    for src, dst in result.http_deps:
        result.edges.append(Edge(src, dst, "chama"))

    result.mermaid = _render_mermaid_simple(result)
    result.human_summary = _human_summary(result)
    return result


def _human_summary(topo: TopologyResult) -> list[str]:
    lines: list[str] = []
    if topo.routes:
        lines.append("**Entrada (usuário → aplicação)**")
        for r in topo.routes:
            tls = "com TLS" if r["tls"] == "sim" else "sem TLS"
            lines.append(
                f"- Usuário acessa `{r['host']}` ({tls}) e chega na aplicação **{r['app']}**."
            )
    else:
        lines.append("**Entrada:** nenhuma Route encontrada (aplicações só internas ao cluster).")

    if topo.http_deps:
        lines.append("")
        lines.append("**Chamadas entre aplicações** (descobertas nos ConfigMaps)")
        for src, dst in topo.http_deps:
            lines.append(f"- **{src}** chama **{dst}**.")
    else:
        lines.append("")
        lines.append("**Chamadas entre aplicações:** nenhuma URL interna explícita nos ConfigMaps.")

    if topo.config_refs:
        lines.append("")
        lines.append("**Configuração injetada nos pods**")
        by_app: dict[str, list[str]] = {}
        for app, ref in topo.config_refs:
            by_app.setdefault(app, []).append(ref)
        for app in sorted(by_app):
            refs = ", ".join(f"`{r}`" for r in sorted(set(by_app[app])))
            lines.append(f"- **{app}** usa {refs}.")
    return lines


def _render_mermaid_simple(topo: TopologyResult) -> str:
    """Diagrama TB simples: Usuário → Apps e Apps → Apps."""
    lines = [
        "flowchart TB",
        '  usuario["Usuario / Internet"]',
    ]
    declared: set[str] = {"usuario"}

    def node(app: str) -> str:
        nid = _safe_id(app)
        if nid not in declared:
            declared.add(nid)
            label = app.replace('"', "'")
            lines.append(f'  {nid}["{label}"]')
        return nid

    for app in topo.apps:
        node(app)

    # Entrada via Route (agrupa por app)
    routed_apps = {r["app"] for r in topo.routes if r.get("app")}
    for app in sorted(routed_apps):
        lines.append(f'  usuario -->|HTTP/HTTPS| {node(app)}')

    # Dependências app→app
    for src, dst in topo.http_deps:
        lines.append(f'  {node(src)} -->|chama| {node(dst)}')

    return "\n".join(lines)


def render_topology_md(ns_name: str, topo: TopologyResult) -> str:
    lines = [
        f"# Arquitetura reversa da aplicação — `{ns_name}`",
        "",
        "Visão simples reconstruída a partir de **Deployments**, **Services**, "
        "**Routes** e **ConfigMaps**.",
        "",
        "## Em poucas palavras",
        "",
    ]
    lines.extend(topo.human_summary or ["Não foi possível montar um resumo."])
    lines.extend(
        [
            "",
            "## Diagrama",
            "",
            "```mermaid",
            topo.mermaid,
            "```",
            "",
            "## Entrada pública (Routes)",
            "",
            "| Host | Aplicação | TLS |",
            "|------|-----------|-----|",
        ]
    )
    for r in topo.routes:
        lines.append(f"| `{r['host']}` | **{r['app']}** | {r['tls']} |")
    if not topo.routes:
        lines.append("| — | — | — |")

    lines.extend(
        [
            "",
            "## Aplicações no namespace",
            "",
        ]
    )
    if topo.apps:
        for app in topo.apps:
            svc = next((s["name"] for s in topo.services if s["target"] == app), "—")
            lines.append(f"- **{app}** (Service: `{svc}`)")
    else:
        lines.append("- Nenhuma aplicação identificada.")
    lines.append("")
    return "\n".join(lines)
