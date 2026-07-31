"""Configuração do agente via variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Carrega .env na raiz do projeto, se existir.
_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    max_iterations: int = 20
    max_file_chars: int = 20_000


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
