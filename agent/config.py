"""Agent configuration via environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root, if it exists.
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


def validate_llm_env() -> None:
    cursor_key = os.getenv("CURSOR_API_KEY", "").strip()
    llm_key = os.getenv("LLM_API_KEY", "").strip()

    if cursor_key or llm_key:
        return

    raise SystemExit(
        "Assessment requires credentials from the system settings API or .env. "
        "Configure SYSTEM_SETTINGS_URL (OpenShift) or fill one of these options:\n"
        "- CURSOR_API_KEY to use Cursor SDK\n"
        "- LLM_API_KEY to use an OpenAI-compatible API\n"
        "See .env.example for the expected format."
    )


def get_settings() -> Settings:
    api_key = os.getenv("LLM_API_KEY", "").strip()
    cursor_key = os.getenv("CURSOR_API_KEY", "").strip()
    if not api_key:
        hint = ""
        if cursor_key:
            hint = (
                "\n\nDetected CURSOR_API_KEY in .env — the OpenAI-compatible ReAct loop "
                "requires LLM_API_KEY. Use Cursor SDK assessment with CURSOR_API_KEY only, "
                "or configure LLM_API_KEY from an OpenAI-compatible provider "
                "(OpenAI, Azure, vLLM, etc.)."
            )
        raise SystemExit(
            "LLM_API_KEY is not set. Configure it in the environment or in .env "
            "(see .env.example)." + hint
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
