"""Inventory of ClusterServiceVersions (OLM operators) in Markdown table form."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.yaml_util import load_yaml_docs, meta_name
from agent.i18n import t

# OLM Subscription.status.state values (console: "Upgrade available" / "Up to date")
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
    if ".v" in csv_name:
        return csv_name.split(".v", 1)[0]
    return csv_name


def _extract_status_state(doc: dict[str, Any]) -> str:
    """Extract `status.state` (OLM property), checking direct and nested forms."""
    status = doc.get("status")
    if not isinstance(status, dict):
        return ""

    direct = status.get("state")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    if direct is not None and not isinstance(direct, (dict, list)):
        text = str(direct).strip()
        if text:
            return text

    # Nested search for a `state:` property inside status.
    found: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "state" and not isinstance(value, (dict, list)):
                    text = str(value).strip()
                    if text:
                        found.append(text)
                else:
                    walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(status)
    return found[0] if found else ""


def _subscription_states(ns: NamespaceArtifacts) -> dict[str, str]:
    """Map installedCSV/currentCSV/package to Subscription.status.state."""
    by_csv: dict[str, str] = {}
    for path in ns.subscriptions:
        for doc in load_yaml_docs(path):
            kind = str(doc.get("kind") or "")
            if kind and kind != "Subscription":
                continue
            state = _extract_status_state(doc)
            if not state:
                continue
            status = doc.get("status") or {}
            for key in ("installedCSV", "currentCSV"):
                csv = str(status.get(key) or "").strip()
                if csv:
                    by_csv[csv] = state
            pkg = str((doc.get("spec") or {}).get("name") or "").strip()
            if pkg:
                by_csv[f"pkg:{pkg}"] = state
    return by_csv


def _packagemanifest_current_csv(ns: NamespaceArtifacts) -> dict[str, str]:
    """Map packageName to currentCSV from the default channel (or first channel)."""
    by_pkg: dict[str, str] = {}
    for path in ns.packagemanifests:
        for doc in load_yaml_docs(path):
            kind = str(doc.get("kind") or "")
            if kind and kind != "PackageManifest":
                continue
            status = doc.get("status") or {}
            pkg = str(status.get("packageName") or meta_name(doc) or "").strip()
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
            if not current and channels and isinstance(channels[0], dict):
                current = str(channels[0].get("currentCSV") or "").strip()
            if current:
                by_pkg[pkg] = current
    return by_pkg


def _resolve_upgrade_state(
    csv_doc: dict[str, Any],
    csv_name: str,
    package: str,
    sub_states: dict[str, str],
    pm_current: dict[str, str],
) -> str:
    # 1) status.state on the YAML itself (CSV or another resource with state)
    own_state = _extract_status_state(csv_doc)
    if own_state:
        return own_state

    # 2) status.state from the matching OLM Subscription
    if csv_name in sub_states:
        return sub_states[csv_name]
    pkg_key = f"pkg:{package}"
    if pkg_key in sub_states:
        return sub_states[pkg_key]

    # 3) Inference via PackageManifest (default channel)
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
                        doc, name, package, sub_states, pm_current
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
    """Section 2.6 — operators present in the namespace (always as a Markdown table)."""
    lines = [
        t("ops.title", name=ns_name),
        "",
        t("ops.counts", scanned=result.scanned, listed=len(result.items)),
        "",
        t("ops.header"),
        t("ops.separator"),
    ]
    if not result.items:
        lines.append(f"| — | — | — | — | — | — | {t('ops.empty')} |")
    else:
        for op in result.items:
            lines.append(
                f"| {op.display_name} | `{op.name}` | `{op.version}` | "
                f"`{op.phase}` | `{op.upgrade_state}` | {op.provider} | `{op.path}` |"
            )
    lines.append("")
    lines.append(
        t(
            "ops.upgrade_note",
            at_latest=_STATE_AT_LATEST,
            upgrade=_STATE_UPGRADE_AVAILABLE,
            unknown=_STATE_UNKNOWN,
        )
    )
    lines.append("")
    lines.append(t("ops.footer"))
    lines.append("")
    return "\n".join(lines)
