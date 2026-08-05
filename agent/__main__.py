"""CLI: PYTHONPATH=src python -m agent --artifacts ./folder [--mode local|llm|embedded]."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from agent.config import get_embedded_settings, validate_llm_env
from agent.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES
from agent.local_analyze import resolve_report_path, run_local_assessment

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


EMBEDDED_DISABLED_MSG = (
    "Embedded mode is not available in container or OpenShift environments yet."
)


def _is_container_or_ocp() -> bool:
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return True
    if Path("/.dockerenv").exists() or Path("/run/.containerenv").exists():
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenShift assessment: local analysis, remote LLM, or local embedded AI."
    )
    parser.add_argument(
        "--artifacts",
        "-a",
        required=True,
        help="Directory containing collected artifacts",
    )
    parser.add_argument(
        "--report",
        "-r",
        default=None,
        help=(
            "Output .md file or output directory "
            "(default: <artifacts>/assessment-report.md)"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("local", "llm", "embedded"),
        default="local",
        help=(
            "local = heuristics without an LLM; "
            "llm = Cursor SDK (CURSOR_API_KEY) or OpenAI-compatible API (LLM_API_KEY); "
            "embedded = heuristics + local OpenAI-compatible model (for example: Ollama/Mistral)"
        ),
    )
    parser.add_argument(
        "--locale",
        choices=SUPPORTED_LOCALES,
        default=DEFAULT_LOCALE,
        help=(
            "Report locale. Supported values: pt-BR, en-US, es-ES, it-IT "
            "(default: pt-BR)"
        ),
    )
    args = parser.parse_args()

    artifacts = Path(args.artifacts)
    report = Path(args.report) if args.report else None
    locale = args.locale

    if args.mode == "local":
        out = run_local_assessment(artifacts, report, locale=locale)
        print(f"[agent] Report written to: {out}")
        return

    if args.mode == "embedded":
        if _is_container_or_ocp():
            raise SystemExit(EMBEDDED_DISABLED_MSG)

        from agent.embedded_assess import run_embedded_assessment

        out = run_embedded_assessment(
            artifacts,
            report,
            get_embedded_settings(),
            locale=locale,
        )
        print(f"[agent] Report written to: {out}")
        return

    validate_llm_env()

    cursor_key = os.getenv("CURSOR_API_KEY", "").strip()
    openai_key = os.getenv("LLM_API_KEY", "").strip()

    if cursor_key:
        from agent.cursor_assess import run_cursor_assessment

        out = run_cursor_assessment(artifacts, report, locale=locale)
        print(f"[agent] Report written to: {out}")
        return

    if openai_key:
        from agent.agent import run_assessment
        from agent.config import get_settings

        settings = get_settings()
        out = run_assessment(artifacts, settings, locale=locale)
        if report is not None:
            dest = resolve_report_path(artifacts, report)
            if out.resolve() != dest:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"[agent] Report copied to: {dest}")
        print(f"[agent] Report written to: {out}")
        return

    raise SystemExit(
        "Could not start llm mode because the .env credentials are empty.\n"
        "Set CURSOR_API_KEY or LLM_API_KEY and try again."
    )


if __name__ == "__main__":
    main()
