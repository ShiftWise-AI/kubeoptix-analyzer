"""Tools for summarizing Kubernetes/OpenShift manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from agent.tools.base import FunctionTool, object_schema
from agent.tools.filesystem import _safe_resolve


def _container_summary(container: dict[str, Any]) -> dict[str, Any]:
    resources = container.get("resources") or {}
    return {
        "name": container.get("name"),
        "image": container.get("image"),
        "ports": container.get("ports"),
        "resources": resources,
        "has_liveness_probe": "livenessProbe" in container,
        "has_readiness_probe": "readinessProbe" in container,
        "has_startup_probe": "startupProbe" in container,
        "env_count": len(container.get("env") or []),
        "env_from_count": len(container.get("envFrom") or []),
    }


def _workload_summary(doc: dict[str, Any]) -> dict[str, Any]:
    meta = doc.get("metadata") or {}
    spec = doc.get("spec") or {}
    template_spec = ((spec.get("template") or {}).get("spec")) or {}
    containers = [
        _container_summary(c) for c in (template_spec.get("containers") or [])
    ]
    return {
        "kind": doc.get("kind"),
        "name": meta.get("name"),
        "namespace": meta.get("namespace"),
        "labels": meta.get("labels"),
        "replicas": spec.get("replicas"),
        "strategy": spec.get("strategy") or spec.get("updateStrategy"),
        "containers": containers,
        "service_account": template_spec.get("serviceAccountName"),
    }


def _route_summary(doc: dict[str, Any]) -> dict[str, Any]:
    meta = doc.get("metadata") or {}
    spec = doc.get("spec") or {}
    return {
        "kind": doc.get("kind"),
        "name": meta.get("name"),
        "namespace": meta.get("namespace"),
        "host": spec.get("host"),
        "to": spec.get("to"),
        "port": spec.get("port"),
        "tls": bool(spec.get("tls")),
        "path": spec.get("path"),
    }


def _service_summary(doc: dict[str, Any]) -> dict[str, Any]:
    meta = doc.get("metadata") or {}
    spec = doc.get("spec") or {}
    return {
        "kind": doc.get("kind"),
        "name": meta.get("name"),
        "namespace": meta.get("namespace"),
        "type": spec.get("type"),
        "selector": spec.get("selector"),
        "ports": spec.get("ports"),
        "cluster_ip": spec.get("clusterIP"),
    }


def _hpa_summary(doc: dict[str, Any]) -> dict[str, Any]:
    meta = doc.get("metadata") or {}
    spec = doc.get("spec") or {}
    return {
        "kind": doc.get("kind"),
        "name": meta.get("name"),
        "namespace": meta.get("namespace"),
        "min_replicas": spec.get("minReplicas"),
        "max_replicas": spec.get("maxReplicas"),
        "scale_target_ref": spec.get("scaleTargetRef"),
        "metrics": spec.get("metrics"),
    }


def _generic_summary(doc: dict[str, Any]) -> dict[str, Any]:
    meta = doc.get("metadata") or {}
    return {
        "kind": doc.get("kind"),
        "apiVersion": doc.get("apiVersion"),
        "name": meta.get("name"),
        "namespace": meta.get("namespace"),
        "labels": meta.get("labels"),
        "keys_in_spec": sorted((doc.get("spec") or {}).keys()),
    }


_WORKLOAD_KINDS = {
    "Deployment",
    "DeploymentConfig",
    "StatefulSet",
    "ReplicaSet",
    "Job",
    "CronJob",
}


def summarize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    kind = doc.get("kind") or ""
    if kind in _WORKLOAD_KINDS:
        return _workload_summary(doc)
    if kind == "Route":
        return _route_summary(doc)
    if kind == "Service":
        return _service_summary(doc)
    if kind in {"HorizontalPodAutoscaler", "HorizontalPodAutoscalerV2"}:
        return _hpa_summary(doc)
    return _generic_summary(doc)


def build_manifest_tools(artifacts_dir: Path) -> list[FunctionTool]:
    def summarize_manifest(path: str) -> str:
        target = _safe_resolve(artifacts_dir, path)
        if not target.is_file():
            return f"File not found: {path}"
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
            docs = list(yaml.safe_load_all(text))
        except Exception as exc:  # noqa: BLE001
            return f"Failed to parse YAML {path}: {exc}"

        summaries = []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            summaries.append(summarize_doc(doc))

        if not summaries:
            return f"No valid YAML documents in {path}"

        return json.dumps(summaries, indent=2, ensure_ascii=False, default=str)

    return [
        FunctionTool(
            name="summarize_manifest",
            description=(
                "Extrai campos-chave de um manifest YAML (replicas, image, probes, "
                "resources, routes, services, HPA)."
            ),
            parameters=object_schema(
                {
                    "path": {
                        "type": "string",
                        "description": "Caminho relativo do arquivo YAML",
                    }
                },
                required=["path"],
            ),
            handler=summarize_manifest,
        )
    ]
