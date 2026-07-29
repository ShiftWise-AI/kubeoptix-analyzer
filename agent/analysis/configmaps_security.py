"""Varredura de ConfigMaps em busca de informações sensíveis."""

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
            "Mover segredos (senhas, tokens, certificados privados) de ConfigMap "
            "para Secret ou cofre externo (Vault/External Secrets), com rotação."
        )
        result.recommendations.append(
            "Garantir que pipelines de coleta continuem mascarando valores sensíveis "
            "antes de compartilhar artefatos."
        )
        result.recommendations.append(
            "Revisar RBAC de leitura de ConfigMaps/Secrets no namespace."
        )
    else:
        result.recommendations.append(
            "Nenhum indício forte de segredo em ConfigMaps nos artefatos "
            "(valores podem já estar sanitizados). Validar processo de build/deploy "
            "para impedir regressão."
        )
        # Ainda assim DB URLs / usuários em CM são risco menor
        result.recommendations.append(
            "Preferir referenciar credenciais de banco via Secret mesmo quando a URL "
            "JDBC permanece no ConfigMap."
        )
    return result


def render_configmaps_md(ns_name: str, result: ConfigMapSecurityResult) -> str:
    lines = [
        f"# Análise de ConfigMaps — informações sensíveis — `{ns_name}`",
        "",
        f"- ConfigMaps analisados: **{result.scanned}**",
        f"- Com dados (`data`/`binaryData`): **{result.with_data}**",
        f"- Achados sensíveis: **{len(result.hits)}**",
        "",
        "## Achados",
        "",
    ]
    if not result.hits:
        lines.append(
            "Nenhuma evidência clara de segredo/certificado/token nos ConfigMaps "
            "analisados (ou dados já sanitizados)."
        )
        lines.append("")
    else:
        lines.extend(
            [
                "| ConfigMap | App | Chave | Categoria | Evidência (truncada) |",
                "|-----------|-----|-------|-----------|----------------------|",
            ]
        )
        for hit in result.hits:
            ev = hit.evidence.replace("|", "\\|")
            lines.append(
                f"| `{hit.configmap}` | `{hit.app}` | `{hit.key}` | {hit.category} | `{ev}` |"
            )
        lines.append("")

    lines.extend(["## Recomendações", ""])
    for idx, rec in enumerate(result.recommendations, start=1):
        lines.append(f"{idx}. {rec}")
    lines.append("")
    return "\n".join(lines)
