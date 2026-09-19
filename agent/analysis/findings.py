"""Configuration findings for workloads and routes."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.yaml_util import app_label, load_yaml_docs, meta_name
from agent.i18n import t


@dataclass
class Finding:
    severity: str  # high | medium | low
    title: str
    detail: str
    path: str = ""
    area: str = "aplicacao"  # infrastructure | application


@dataclass
class FindingsResult:
    items: list[Finding] = field(default_factory=list)


def _image_is_latest(image: str | None) -> bool:
    if not image:
        return False
    if "@" in image:
        return False
    tag = image.rsplit(":", 1)[-1] if ":" in image else "latest"
    return tag in {"latest", "LATEST"} or ":" not in image


def analyze_findings(ns: NamespaceArtifacts) -> FindingsResult:
    result = FindingsResult()
    for path in ns.deployments:
        rel = path.name
        for doc in load_yaml_docs(path):
            kind = doc.get("kind") or "Deployment"
            name = meta_name(doc)
            app = app_label(doc, name)
            spec = doc.get("spec") or {}
            replicas = spec.get("replicas")
            template_spec = ((spec.get("template") or {}).get("spec")) or {}
            containers = template_spec.get("containers") or []
            for c in containers:
                cname = c.get("name") or "container"
                image = c.get("image")
                resources = c.get("resources") or {}
                limits = resources.get("limits") or {}
                requests = resources.get("requests") or {}
                if _image_is_latest(image):
                    result.items.append(
                        Finding(
                            "medio",
                            t("finding.latest_title", app=app),
                            t(
                                "finding.latest_detail",
                                container=cname,
                                image=image,
                            ),
                            rel,
                            "aplicacao",
                        )
                    )
                if "readinessProbe" not in c:
                    result.items.append(
                        Finding(
                            "alto",
                            t("finding.readiness_title", app=app),
                            t("finding.readiness_detail", container=cname),
                            rel,
                            "aplicacao",
                        )
                    )
                if "livenessProbe" not in c:
                    result.items.append(
                        Finding(
                            "medio",
                            t("finding.liveness_title", app=app),
                            t("finding.liveness_detail", container=cname),
                            rel,
                            "aplicacao",
                        )
                    )
                if not limits.get("memory") and not limits.get("cpu"):
                    result.items.append(
                        Finding(
                            "alto",
                            t("finding.limits_title", app=app),
                            t("finding.limits_detail", container=cname),
                            rel,
                            "infraestrutura",
                        )
                    )
                if not requests.get("memory") and not requests.get("cpu"):
                    result.items.append(
                        Finding(
                            "medio",
                            t("finding.requests_title", app=app),
                            t("finding.requests_detail", container=cname),
                            rel,
                            "infraestrutura",
                        )
                    )
            if replicas == 1:
                result.items.append(
                    Finding(
                        "baixo",
                        t("finding.replica_title", app=app),
                        t("finding.replica_detail", kind=kind, name=name),
                        rel,
                        "infraestrutura",
                    )
                )

    for path in ns.routes:
        for doc in load_yaml_docs(path):
            name = meta_name(doc)
            host = ((doc.get("spec") or {}).get("host")) or t("route.no_host")
            tls = (doc.get("spec") or {}).get("tls")
            if not tls:
                result.items.append(
                    Finding(
                        "alto",
                        t("finding.tls_title", name=name),
                        t("finding.tls_detail", host=host),
                        path.name,
                        "infraestrutura",
                    )
                )
            elif (tls or {}).get("insecureEdgeTerminationPolicy") == "Allow":
                result.items.append(
                    Finding(
                        "medio",
                        t("finding.insecure_title", name=name),
                        t("finding.insecure_detail", host=host),
                        path.name,
                        "infraestrutura",
                    )
                )
    return result
