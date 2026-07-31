"""Inventário de ClusterServiceVersions (operadores OLM) em tabela Markdown."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.yaml_util import load_yaml_docs, meta_name

# Estados OLM Subscription.status.state (console: "Upgrade available" / "Up to date")
_STATE_AT_LATEST = "AtLatestKnown"
_STATE_UPGRADE_AVAILABLE = "UpgradeAvailable"
_STATE_UNKNOWN = "—"


@dataclass
class OperatorInfo:
    name: str
    display_name: str
    version: str
    phase: str
    provider: str
    upgrade_state: str
    path: str


@dataclass
class OperatorsResult:
    items: list[OperatorInfo] = field(default_factory=list)
    scanned: int = 0


def _provider_name(spec: dict[str, Any]) -> str:
    provider = spec.get("provider")
    if isinstance(provider, dict):
        return str(provider.get("name") or "").strip()
    if provider is None:
        return ""
    return str(provider).strip()


def _package_name(doc: dict[str, Any], csv_name: str) -> str:
    labels = (doc.get("metadata") or {}).get("labels") or {}
    ann = (doc.get("metadata") or {}).get("annotations") or {}
    for key in (
        "operators.operatorframework.io.bundle.package.v1",
        "operators.coreos.com/package",
    ):
        val = str(ann.get(key) or labels.get(key) or "").strip()
        if val:
            return val
    # Heurística: nome do CSV até ".v" (ex.: redis-operator.v0.15.1 → redis-operator)
    if ".v" in csv_name:
        return csv_name.split(".v", 1)[0]
    return csv_name


def _subscription_states(ns: NamespaceArtifacts) -> dict[str, str]:
    """Mapa installedCSV/currentCSV → status.state da Subscription."""
    by_csv: dict[str, str] = {}
    for path in ns.subscriptions:
        for doc in load_yaml_docs(path):
            kind = str(doc.get("kind") or "")
            if kind and kind != "Subscription":
                continue
            status = doc.get("status") or {}
            state = str(status.get("state") or "").strip()
            if not state:
                continue
            for key in ("installedCSV", "currentCSV"):
                csv = str(status.get(key) or "").strip()
                if csv:
                    by_csv[csv] = state
            # Também indexa pelo package da Subscription (spec.name)
            pkg = str((doc.get("spec") or {}).get("name") or "").strip()
            if pkg and pkg not in by_csv:
                by_csv[f"pkg:{pkg}"] = state
    return by_csv


def _packagemanifest_current_csv(ns: NamespaceArtifacts) -> dict[str, str]:
    """Mapa packageName → currentCSV do canal default (ou primeiro canal)."""
    by_pkg: dict[str, str] = {}
    for path in ns.packagemanifests:
        for doc in load_yaml_docs(path):
            kind = str(doc.get("kind") or "")
            if kind and kind != "PackageManifest":
                continue
            status = doc.get("status") or {}
            pkg = str(
                status.get("packageName")
                or meta_name(doc)
                or ""
            ).strip()
            if not pkg:
                continue
            default = str(status.get("defaultChannel") or "").strip()
            channels = status.get("channels") or []
            current = ""
            for ch in channels:
                if not isinstance(ch, dict):
                    continue
                if default and str(ch.get("name") or "") == default:
                    current = str(ch.get("currentCSV") or "").strip()
                    break
            if not current and channels:
                ch0 = channels[0] if isinstance(channels[0], dict) else {}
                current = str(ch0.get("currentCSV") or "").strip()
            if current:
                by_pkg[pkg] = current
    return by_pkg


def _resolve_upgrade_state(
    csv_name: str,
    package: str,
    sub_states: dict[str, str],
    pm_current: dict[str, str],
) -> str:
    # 1) Subscription.status.state (fonte canônica OLM)
    if csv_name in sub_states:
        return sub_states[csv_name]
    pkg_key = f"pkg:{package}"
    if pkg_key in sub_states:
        return sub_states[pkg_key]

    # 2) Inferência via PackageManifest (canal default)
    latest = pm_current.get(package)
    if not latest:
        return _STATE_UNKNOWN
    if latest == csv_name:
        return _STATE_AT_LATEST
    return _STATE_UPGRADE_AVAILABLE


def analyze_operators(ns: NamespaceArtifacts) -> OperatorsResult:
    result = OperatorsResult()
    sub_states = _subscription_states(ns)
    pm_current = _packagemanifest_current_csv(ns)

    for path in ns.clusterserviceversions:
        result.scanned += 1
        for doc in load_yaml_docs(path):
            kind = str(doc.get("kind") or "")
            if kind and kind != "ClusterServiceVersion":
                continue
            name = meta_name(doc)
            if not name:
                continue
            spec = doc.get("spec") or {}
            status = doc.get("status") or {}
            package = _package_name(doc, name)
            result.items.append(
                OperatorInfo(
                    name=name,
                    display_name=str(spec.get("displayName") or name).strip(),
                    version=str(spec.get("version") or "—").strip() or "—",
                    phase=str(status.get("phase") or "—").strip() or "—",
                    provider=_provider_name(spec) or "—",
                    upgrade_state=_resolve_upgrade_state(
                        name, package, sub_states, pm_current
                    ),
                    path=_rel_path(ns.root, path),
                )
            )
    result.items.sort(key=lambda o: (o.display_name.lower(), o.name.lower()))
    return result


def _rel_path(ns_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ns_root.resolve()))
    except ValueError:
        return str(path)


def render_operators_md(ns_name: str, result: OperatorsResult) -> str:
    """Seção 2.6 — operadores presentes (sempre em tabela Markdown)."""
    lines = [
        f"### 2.6 Operadores presentes no namespace (ClusterServiceVersions) — `{ns_name}`",
        "",
        f"CSVs analisados: **{result.scanned}** · listados: **{len(result.items)}**",
        "",
        (
            "| Operador (displayName) | CSV | Versão | Phase | Upgrade disponível | "
            "Provider | Evidência |"
        ),
        (
            "|------------------------|-----|--------|-------|--------------------|"
            "----------|-----------|"
        ),
    ]
    if not result.items:
        lines.append(
            "| — | — | — | — | — | — | Nenhum CSV em `resources/clusterserviceversions*` |"
        )
    else:
        for op in result.items:
            lines.append(
                f"| {op.display_name} | `{op.name}` | `{op.version}` | "
                f"`{op.phase}` | `{op.upgrade_state}` | {op.provider} | `{op.path}` |"
            )
    lines.append("")
    lines.append(
        "Coluna **Upgrade disponível**: `status.state` da Subscription OLM "
        f"(`{_STATE_AT_LATEST}`, `{_STATE_UPGRADE_AVAILABLE}`, "
        "`UpgradePending`, `UpgradeFailed`) quando houver Subscription nos "
        "artefatos; senão, inferido pelo `currentCSV` do PackageManifest "
        f"(canal default); `{_STATE_UNKNOWN}` se não houver evidência."
    )
    lines.append("")
    lines.append(
        "Os CSVs indicam operadores disponíveis via OLM no escopo coletado; "
        "não implicam, por si só, ServiceMonitor/PodMonitor/PrometheusRule "
        "configurados para as aplicações do namespace."
    )
    lines.append("")
    return "\n".join(lines)
