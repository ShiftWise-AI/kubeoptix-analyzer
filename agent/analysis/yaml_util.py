"""YAML helpers and Kubernetes resource-unit utilities."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def load_yaml_docs(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        docs = list(yaml.safe_load_all(text))
    except Exception:  # noqa: BLE001
        return []
    return [d for d in docs if isinstance(d, dict)]


def meta_name(doc: dict[str, Any]) -> str:
    return str(((doc.get("metadata") or {}).get("name")) or "")


def meta_namespace(doc: dict[str, Any]) -> str:
    return str(((doc.get("metadata") or {}).get("namespace")) or "")


def meta_labels(doc: dict[str, Any]) -> dict[str, str]:
    labels = (doc.get("metadata") or {}).get("labels") or {}
    return {str(k): str(v) for k, v in labels.items()}


def app_label(doc: dict[str, Any], fallback: str = "") -> str:
    labels = meta_labels(doc)
    for key in ("app", "app.kubernetes.io/name", "name"):
        if labels.get(key):
            return labels[key]
    return fallback or meta_name(doc)


def parse_cpu(value: Any) -> float | None:
    """Return CPU in millicores."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("m"):
            return float(s[:-1])
        return float(s) * 1000.0
    except ValueError:
        return None


def parse_memory_mi(value: Any) -> float | None:
    """Return memory in MiB."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        units = {
            "Ki": 1 / 1024,
            "Mi": 1.0,
            "Gi": 1024.0,
            "Ti": 1024.0 * 1024,
            "K": 1000 / (1024 * 1024) * 1000,  # rough approximation
            "M": 1000 / 1024,
            "G": 1000 * 1000 / 1024,
        }
        for suffix, factor in units.items():
            if s.endswith(suffix):
                return float(s[: -len(suffix)]) * factor
        # raw bytes
        return float(s) / (1024 * 1024)
    except ValueError:
        return None


def format_cpu_m(millicores: float | None) -> str:
    if millicores is None:
        return "—"
    if millicores >= 1000:
        return f"{millicores / 1000:.2f}"
    return f"{int(millicores)}m"


def format_mem_mi(mib: float | None) -> str:
    if mib is None:
        return "—"
    if mib >= 1024:
        return f"{mib / 1024:.2f}Gi"
    return f"{mib:.0f}Mi"


_SVC_URL_RE = re.compile(
    r"https?://([a-z0-9][a-z0-9-]*)(?:\.[a-z0-9-]+)?\.svc(?:\.[a-z0-9.-]+)?(?::\d+)?",
    re.IGNORECASE,
)


def extract_service_refs_from_text(text: str) -> set[str]:
    return {m.group(1) for m in _SVC_URL_RE.finditer(text or "")}
