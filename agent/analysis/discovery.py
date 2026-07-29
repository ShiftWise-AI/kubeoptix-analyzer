"""Descoberta do layout de artefatos (collector antigo ou resources/)."""

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
    log_files: list[Path] = field(default_factory=list)
    service_monitors: list[Path] = field(default_factory=list)
    pod_monitors: list[Path] = field(default_factory=list)
    prometheus_rules: list[Path] = field(default_factory=list)


def _glob_resource_dirs(resources: Path, *names: str) -> list[Path]:
    files: list[Path] = []
    for name in names:
        d = resources / name
        if d.is_dir():
            files.extend(sorted(d.glob("*.yaml")))
            files.extend(sorted(d.glob("*.yml")))
    return files


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
        ns.service_monitors = _glob_resource_dirs(
            resources, "servicemonitors.monitoring.coreos.com"
        )
        ns.pod_monitors = _glob_resource_dirs(
            resources, "podmonitors.monitoring.coreos.com"
        )
        ns.prometheus_rules = _glob_resource_dirs(
            resources, "prometheusrules.monitoring.coreos.com"
        )

    for logs_dir_name in ("pods-logs", "pod-logs"):
        logs_dir = root / logs_dir_name
        if logs_dir.is_dir():
            ns.log_files.extend(sorted(logs_dir.rglob("*.log")))
            ns.log_files.extend(sorted(logs_dir.rglob("*.txt")))

    # Layout antigo: apps/<app>/<tipo>/
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
                ("pod-logs", "log_files"),
            ):
                d = app_dir / sub
                if not d.is_dir():
                    continue
                files = sorted(d.rglob("*"))
                files = [f for f in files if f.is_file()]
                getattr(ns, attr).extend(files)

    # Dedup paths
    for attr in (
        "deployments",
        "services",
        "routes",
        "configmaps",
        "pods",
        "log_files",
        "service_monitors",
        "pod_monitors",
        "prometheus_rules",
    ):
        seen: set[Path] = set()
        unique: list[Path] = []
        for p in getattr(ns, attr):
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                unique.append(p)
        setattr(ns, attr, unique)

    return ns


def discover_namespaces(artifacts_dir: Path) -> list[NamespaceArtifacts]:
    artifacts_dir = artifacts_dir.resolve()
    # Caso 1: o próprio diretório é um namespace (tem resources/ ou pods-logs/)
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
        # fallback: tratar raiz como namespace genérico
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
