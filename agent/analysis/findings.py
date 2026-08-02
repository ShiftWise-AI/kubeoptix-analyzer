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
                            f"{app}: imagem :latest",
                            f"Contêiner `{cname}` usa `{image}`.",
                            rel,
                            "aplicacao",
                        )
                    )
                if "readinessProbe" not in c:
                    result.items.append(
                        Finding(
                            "alto",
                            f"{app}: sem readinessProbe",
                            f"Contêiner `{cname}` sem probe de prontidão.",
                            rel,
                            "aplicacao",
                        )
                    )
                if "livenessProbe" not in c:
                    result.items.append(
                        Finding(
                            "medio",
                            f"{app}: sem livenessProbe",
                            f"Contêiner `{cname}` sem probe de vitalidade.",
                            rel,
                            "aplicacao",
                        )
                    )
                if not limits.get("memory") and not limits.get("cpu"):
                    result.items.append(
                        Finding(
                            "alto",
                            f"{app}: sem resource limits",
                            f"Contêiner `{cname}` sem limits de CPU/memória.",
                            rel,
                            "infraestrutura",
                        )
                    )
                if not requests.get("memory") and not requests.get("cpu"):
                    result.items.append(
                        Finding(
                            "medio",
                            f"{app}: sem resource requests",
                            f"Contêiner `{cname}` sem requests de CPU/memória.",
                            rel,
                            "infraestrutura",
                        )
                    )
            if replicas == 1:
                result.items.append(
                    Finding(
                        "baixo",
                        f"{app}: uma única réplica",
                        f"{kind}/{name} com replicas=1 — risco de indisponibilidade.",
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
                        f"Route/{name}: sem TLS",
                        f"Host `{host}` exposto sem TLS.",
                        path.name,
                        "infraestrutura",
                    )
                )
            elif (tls or {}).get("insecureEdgeTerminationPolicy") == "Allow":
                result.items.append(
                    Finding(
                        "medio",
                        f"Route/{name}: HTTP inseguro permitido",
                        f"Host `{host}` com `insecureEdgeTerminationPolicy=Allow`.",
                        path.name,
                        "infraestrutura",
                    )
                )
    return result
