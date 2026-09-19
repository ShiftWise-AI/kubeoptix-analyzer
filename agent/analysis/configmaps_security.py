"""Scan of ConfigMaps for sensitive information."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.yaml_util import app_label, load_yaml_docs, meta_name
from agent.i18n import t

SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|private[_-]?key|access[_-]?key|"
    r"client[_-]?secret|auth|credential|keystore|truststore|cert|certificate|"
    r"BEGIN\s+(RSA\s+)?PRIVATE\s+KEY|BEGIN\s+CERTIFICATE|jdbc:.*password)",
    re.IGNORECASE,
)

SENSITIVE_VALUE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("certificado_pem", re.compile(r"-----BEGIN CERTIFICATE-----")),
    ("chave_privada_pem", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)?PRIVATE KEY-----")),
    ("token_jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("bearer", re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE)),
    ("senha_explicita", re.compile(r"(password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE)),
    ("connection_string_credencial", re.compile(r"(user|uid|pwd|password)=", re.IGNORECASE)),
]


@dataclass
class SensitiveHit:
    configmap: str
    app: str
    key: str
    category: str
    evidence: str


@dataclass
class ConfigMapSecurityResult:
    hits: list[SensitiveHit] = field(default_factory=list)
    scanned: int = 0
    with_data: int = 0
    recommendations: list[str] = field(default_factory=list)


def analyze_configmaps(ns: NamespaceArtifacts) -> ConfigMapSecurityResult:
    result = ConfigMapSecurityResult()
    for path in ns.configmaps:
        result.scanned += 1
        for doc in load_yaml_docs(path):
            name = meta_name(doc) or path.stem
            app = app_label(doc, name)
            data = doc.get("data") or {}
            binary = doc.get("binaryData") or {}
            if data or binary:
                result.with_data += 1
            for key, value in {**data, **{k: "<binary>" for k in binary}}.items():
                key_s = str(key)
                val_s = str(value)
                if SENSITIVE_KEY_RE.search(key_s):
                    result.hits.append(
                        SensitiveHit(
                            name,
                            app,
                            key_s,
                            "chave_suspeita",
                            t("cm.suspicious_key", key=key_s),
                        )
                    )
                for category, regex in SENSITIVE_VALUE_PATTERNS:
                    if regex.search(val_s):
                        evidence = val_s.strip().replace("\n", " ")
                        if len(evidence) > 80:
                            evidence = evidence[:80] + "…"
                        result.hits.append(
                            SensitiveHit(
                                name,
                                app,
                                key_s,
                                category,
                                evidence,
                            )
                        )
                        break

    if result.hits:
        result.recommendations.extend(
            [
                t("cm.rec.move"),
                t("cm.rec.mask"),
                t("cm.rec.rbac"),
            ]
        )
    else:
        result.recommendations.extend(
            [
                t("cm.rec.none"),
                t("cm.rec.jdbc"),
            ]
        )
    return result


def render_configmaps_md(ns_name: str, result: ConfigMapSecurityResult) -> str:
    lines = [
        t("cm.title", name=ns_name),
        "",
        t("cm.scanned", count=result.scanned),
        t("cm.with_data", count=result.with_data),
        t("cm.hits", count=len(result.hits)),
        "",
        t("cm.findings"),
        "",
    ]
    if not result.hits:
        lines.append(t("cm.none"))
        lines.append("")
    else:
        lines.append(t("cm.table"))
        for hit in result.hits:
            ev = hit.evidence.replace("|", "\\|")
            category = t(f"cm.cat.{hit.category}")
            lines.append(
                f"| `{hit.configmap}` | `{hit.app}` | `{hit.key}` | {category} | `{ev}` |"
            )
        lines.append("")

    lines.extend(["", t("cm.recommendations"), ""])
    for idx, rec in enumerate(result.recommendations, start=1):
        lines.append(f"{idx}. {rec}")
    lines.append("")
    return "\n".join(lines)
