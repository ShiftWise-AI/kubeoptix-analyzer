"""Artifact layout discovery (legacy collector or resources/ layout)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agent.analysis.yaml_util import (
    app_label,
    load_yaml_docs,
    meta_name,
)


@dataclass
class NamespaceArtifacts:
    name: str
    root: Path
    deployments: list[Path] = field(default_factory=list)
    services: list[Path] = field(default_factory=list)
    routes: list[Path] = field(default_factory=list)
    configmaps: list[Path] = field(default_factory=list)
    pods: list[Path] = field(default_factory=list)
    hpas: list[Path] = field(default_factory=list)
    log_files: list[Path] = field(default_factory=list)
    service_monitors: list[Path] = field(default_factory=list)
    pod_monitors: list[Path] = field(default_factory=list)
    prometheus_rules: list[Path] = field(default_factory=list)
    clusterserviceversions: list[Path] = field(default_factory=list)
    subscriptions: list[Path] = field(default_factory=list)
    packagemanifests: list[Path] = field(default_factory=list)


def _glob_resource_dirs(resources: Path, *names: str) -> list[Path]:
    files: list[Path] = []
    for name in names:
        d = resources / name
        if d.is_dir():
            files.extend(sorted(d.glob("*.yaml")))
            files.extend(sorted(d.glob("*.yml")))
    return files


def _path_layout_priority(path: Path) -> int:
    """Prefer canonical resources/ layout over legacy apps/ duplicates."""
    parts = path.parts
    if "resources" in parts:
        return 0
    if "apps" in parts:
        return 1
    return 2


def _resource_identity(path: Path) -> tuple[str, str] | None:
    docs = load_yaml_docs(path)
    if not docs:
        return None
    doc = docs[0]
    kind = str(doc.get("kind") or "")
    name = meta_name(doc)
    if not kind or not name:
        return None
    return (kind, name)


def _dedupe_resource_paths(paths: list[Path]) -> list[Path]:
    """Drop duplicate manifests collected from both resources/ and apps/ layouts."""
    by_key: dict[tuple[str, str], Path] = {}
    order: list[tuple[str, str]] = []
    for path in paths:
        key = _resource_identity(path) or ("__path__", str(path.resolve()))
        if key not in by_key:
            by_key[key] = path
            order.append(key)
            continue
        if _path_layout_priority(path) < _path_layout_priority(by_key[key]):
            by_key[key] = path
    return [by_key[key] for key in order]


def _dedupe_log_paths(paths: list[Path]) -> list[Path]:
    by_name: dict[str, Path] = {}
    order: list[str] = []
    for path in paths:
        name = path.name
        if name not in by_name:
            by_name[name] = path
            order.append(name)
            continue
        if _path_layout_priority(path) < _path_layout_priority(by_name[name]):
            by_name[name] = path
    return [by_name[name] for name in order]


def _discover_namespace_root(root: Path, name: str) -> NamespaceArtifacts:
    ns = NamespaceArtifacts(name=name, root=root)
    resources = root / "resources"
    if resources.is_dir():
        ns.deployments = _glob_resource_dirs(
            resources,
            "deployments.apps",
            "deployments",
            "deploymentconfigs.apps.openshift.io",
            "deploymentconfigs",
            "statefulsets.apps",
            "statefulsets",
        )
        ns.services = _glob_resource_dirs(resources, "services")
        ns.routes = _glob_resource_dirs(
            resources, "routes.route.openshift.io", "routes"
        )
        ns.configmaps = _glob_resource_dirs(resources, "configmaps")
        ns.pods = _glob_resource_dirs(resources, "pods")
        ns.hpas = _glob_resource_dirs(
            resources,
            "horizontalpodautoscalers.autoscaling",
            "horizontalpodautoscalers",
            "hpa",
        )
        ns.service_monitors = _glob_resource_dirs(
            resources, "servicemonitors.monitoring.coreos.com"
        )
        ns.pod_monitors = _glob_resource_dirs(
            resources, "podmonitors.monitoring.coreos.com"
        )
        ns.prometheus_rules = _glob_resource_dirs(
            resources, "prometheusrules.monitoring.coreos.com"
        )
        ns.clusterserviceversions = _glob_resource_dirs(
            resources,
            "clusterserviceversions.operators.coreos.com",
            "clusterserviceversions",
        )
        ns.subscriptions = _glob_resource_dirs(
            resources,
            "subscriptions.operators.coreos.com",
            "subscriptions",
        )
        ns.packagemanifests = _glob_resource_dirs(
            resources,
            "packagemanifests.packages.operators.coreos.com",
            "packagemanifests",
        )

    for logs_dir_name in ("pods-logs", "pod-logs"):
        logs_dir = root / logs_dir_name
        if logs_dir.is_dir():
            ns.log_files.extend(sorted(logs_dir.rglob("*.log")))
            ns.log_files.extend(sorted(logs_dir.rglob("*.txt")))

    # Legacy layout: apps/<app>/<type>/
    apps = root / "apps"
    if apps.is_dir():
        for app_dir in sorted(p for p in apps.iterdir() if p.is_dir()):
            for sub, attr in (
                ("deployments", "deployments"),
                ("deploymentconfigs", "deployments"),
                ("statefulsets", "deployments"),
                ("services", "services"),
                ("routes", "routes"),
                ("configmaps", "configmaps"),
                ("hpa", "hpas"),
                ("pod-logs", "log_files"),
            ):
                d = app_dir / sub
                if not d.is_dir():
                    continue
                files = sorted(d.rglob("*"))
                files = [f for f in files if f.is_file()]
                getattr(ns, attr).extend(files)

    # Deduplicate paths (same file) and resource manifests (resources/ + apps/).
    for attr in (
        "deployments",
        "services",
        "routes",
        "configmaps",
        "pods",
        "hpas",
        "service_monitors",
        "pod_monitors",
        "prometheus_rules",
        "clusterserviceversions",
        "subscriptions",
        "packagemanifests",
    ):
        setattr(ns, attr, _dedupe_resource_paths(getattr(ns, attr)))
    ns.log_files = _dedupe_log_paths(ns.log_files)

    return ns


def discover_namespaces(artifacts_dir: Path) -> list[NamespaceArtifacts]:
    artifacts_dir = artifacts_dir.resolve()
    # Case 1: the directory itself is a namespace (has resources/ or pods-logs/).
    if (artifacts_dir / "resources").is_dir() or (artifacts_dir / "pods-logs").is_dir():
        return [_discover_namespace_root(artifacts_dir, artifacts_dir.name)]

    namespaces: list[NamespaceArtifacts] = []
    for child in sorted(artifacts_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if (child / "resources").is_dir() or (child / "apps").is_dir() or (
            child / "pods-logs"
        ).is_dir():
            namespaces.append(_discover_namespace_root(child, child.name))
    if not namespaces:
        # Fallback: treat the root as a generic namespace.
        namespaces.append(_discover_namespace_root(artifacts_dir, artifacts_dir.name))
    return namespaces


def list_apps(ns: NamespaceArtifacts) -> list[str]:
    apps: set[str] = set()
    skip = {
        "kube-root-ca.crt",
        "openshift-service-ca.crt",
        "kube-root-ca",
        "openshift-service-ca",
    }
    for path in ns.deployments + ns.services + ns.routes:
        for doc in load_yaml_docs(path):
            name = app_label(doc, meta_name(doc))
            if name and name not in skip:
                apps.add(name)
    return sorted(apps)
