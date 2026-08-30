"""Scan of ConfigMaps for sensitive information."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.yaml_util import app_label, load_yaml_docs, meta_name

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
                            f"Nome da chave sugere segredo: `{key_s}`",
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
        result.recommendations.append(
            "Move secrets (passwords, tokens, private certificates) from ConfigMap "
            "to a Secret or external vault (Vault/External Secrets), with rotation."
        )
        result.recommendations.append(
            "Ensure collection pipelines continue masking sensitive values before "
            "sharing artifacts."
        )
        result.recommendations.append(
            "Review RBAC for reading ConfigMaps/Secrets in the namespace."
        )
    else:
        result.recommendations.append(
            "No strong evidence of secrets in ConfigMaps in the artifacts "
            "(values may already be sanitized). Validate the build/deploy process to "
            "prevent regression."
        )
        # Database URLs / users in a ConfigMap remain a lower risk, but should still be handled carefully.
        result.recommendations.append(
            "Prefer referencing database credentials via Secret even when the JDBC URL "
            "remains in the ConfigMap."
        )
    return result


def render_configmaps_md(ns_name: str, result: ConfigMapSecurityResult) -> str:
    lines = [
        f"# ConfigMap analysis — sensitive information — `{ns_name}`",
        "",
        f"- ConfigMaps analyzed: **{result.scanned}**",
        f"- With data (`data`/`binaryData`): **{result.with_data}**",
        f"- Sensitive findings: **{len(result.hits)}**",
        "",
        "## Findings",
        "",
    ]
    if not result.hits:
        lines.append(
            "No clear evidence of secrets/certificates/tokens in the analyzed ConfigMaps "
            "(or the data is already sanitized)."
        )
        lines.append("")
    else:
        lines.extend(
            [
                "| ConfigMap | App | Key | Category | Evidence (truncated) |",
                "|-----------|-----|-----|----------|----------------------|",
            ]
        )
        for hit in result.hits:
            ev = hit.evidence.replace("|", "\\|")
            lines.append(
                f"| `{hit.configmap}` | `{hit.app}` | `{hit.key}` | {hit.category} | `{ev}` |"
            )
        lines.append("")

    lines.extend(["## Recommendations", ""])
    for idx, rec in enumerate(result.recommendations, start=1):
        lines.append(f"{idx}. {rec}")
    lines.append("")
    return "\n".join(lines)
