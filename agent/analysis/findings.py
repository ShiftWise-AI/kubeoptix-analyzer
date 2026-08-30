"""Configuration findings for workloads and routes."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.yaml_util import app_label, load_yaml_docs, meta_name


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
                            f"{app}: :latest image",
                            f"Container `{cname}` uses `{image}`.",
                            rel,
                            "aplicacao",
                        )
                    )
                if "readinessProbe" not in c:
                    result.items.append(
                        Finding(
                            "alto",
                            f"{app}: missing readinessProbe",
                            f"Container `{cname}` is missing a readiness probe.",
                            rel,
                            "aplicacao",
                        )
                    )
                if "livenessProbe" not in c:
                    result.items.append(
                        Finding(
                            "medio",
                            f"{app}: missing livenessProbe",
                            f"Container `{cname}` is missing a liveness probe.",
                            rel,
                            "aplicacao",
                        )
                    )
                if not limits.get("memory") and not limits.get("cpu"):
                    result.items.append(
                        Finding(
                            "alto",
                            f"{app}: missing resource limits",
                            f"Container `{cname}` is missing CPU/memory limits.",
                            rel,
                            "infraestrutura",
                        )
                    )
                if not requests.get("memory") and not requests.get("cpu"):
                    result.items.append(
                        Finding(
                            "medio",
                            f"{app}: missing resource requests",
                            f"Container `{cname}` is missing CPU/memory requests.",
                            rel,
                            "infraestrutura",
                        )
                    )
            if replicas == 1:
                result.items.append(
                    Finding(
                        "baixo",
                        f"{app}: single replica",
                        f"{kind}/{name} has replicas=1 — availability risk.",
                        rel,
                        "infraestrutura",
                    )
                )

    for path in ns.routes:
        for doc in load_yaml_docs(path):
            name = meta_name(doc)
            host = ((doc.get("spec") or {}).get("host")) or "(sem host)"
            tls = (doc.get("spec") or {}).get("tls")
            if not tls:
                result.items.append(
                    Finding(
                        "alto",
                        f"Route/{name}: missing TLS",
                        f"Host `{host}` is exposed without TLS.",
                        path.name,
                        "infraestrutura",
                    )
                )
            elif (tls or {}).get("insecureEdgeTerminationPolicy") == "Allow":
                result.items.append(
                    Finding(
                        "medio",
                        f"Route/{name}: insecure HTTP allowed",
                        f"Host `{host}` has `insecureEdgeTerminationPolicy=Allow`.",
                        path.name,
                        "infraestrutura",
                    )
                )
    return result
