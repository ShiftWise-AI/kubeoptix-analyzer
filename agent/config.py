"""Configuração do agente via variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

# Carrega .env na raiz do projeto, se existir.
_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"
load_dotenv(_ENV_FILE)


@dataclass(frozen=True)
class Settings:
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    max_iterations: int = 20
    max_file_chars: int = 20_000


@dataclass(frozen=True)
class EmbeddedSettings:
    api_key: str
    base_url: str
    model: str
    timeout_s: int = 120


def validate_llm_env() -> None:
    if not _ENV_FILE.is_file():
        raise SystemExit(
            "Arquivo .env nao encontrado na raiz do projeto. "
            "Crie o arquivo a partir de .env.example e preencha as variaveis do modo llm."
        )

    values = dotenv_values(_ENV_FILE)
    cursor_key = str(values.get("CURSOR_API_KEY") or "").strip()
    llm_key = str(values.get("LLM_API_KEY") or "").strip()

    if cursor_key or llm_key:
        return

    raise SystemExit(
        "Modo llm requer credenciais no .env. Preencha uma destas opcoes:\n"
        "- CURSOR_API_KEY para usar Cursor SDK\n"
        "- LLM_API_KEY para usar uma API OpenAI-compatible\n"
        "Veja .env.example para o formato esperado."
    )


def get_settings() -> Settings:
    api_key = os.getenv("LLM_API_KEY", "").strip()
    cursor_key = os.getenv("CURSOR_API_KEY", "").strip()
    if not api_key:
        hint = ""
        if cursor_key:
            hint = (
                "\n\nDetectei CURSOR_API_KEY no .env — ela NÃO funciona com --mode llm.\n"
                "Use --mode local (recomendado) ou configure LLM_API_KEY de um "
                "provedor OpenAI-compatible (OpenAI, Azure, vLLM, etc.)."
            )
        raise SystemExit(
            "LLM_API_KEY não definida. Configure no ambiente ou em .env "
            "(veja .env.example)." + hint
        )

    return Settings(
        llm_api_key=api_key,
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip(
            "/"
        ),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "20")),
        max_file_chars=int(os.getenv("AGENT_MAX_FILE_CHARS", "20000")),
    )


def get_embedded_settings() -> EmbeddedSettings:
    return EmbeddedSettings(
        api_key=os.getenv("EMBEDDED_API_KEY", "ollama").strip() or "ollama",
        base_url=os.getenv("EMBEDDED_BASE_URL", "http://127.0.0.1:11434/v1").rstrip(
            "/"
        ),
        model=os.getenv("EMBEDDED_MODEL", "mistral").strip() or "mistral",
        timeout_s=int(os.getenv("EMBEDDED_TIMEOUT_S", "120")),
    )
