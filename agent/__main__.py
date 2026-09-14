"""CLI: PYTHONPATH=src python -m agent --artifacts ./folder [--report path]."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from agent.config import validate_llm_env
from agent.local_analyze import resolve_report_path
from agent.system_settings import SettingsLoadError, load_runtime_settings

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenShift assessment via generative LLM (Cursor SDK or OpenAI-compatible API)."
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
        "--local",
        action="store_true",
        help="Run deterministic local analysis (no LLM, with embedded PNG charts)",
    )
    args = parser.parse_args()

    artifacts = Path(args.artifacts)
    report = Path(args.report) if args.report else None

    if args.local:
        from agent.local_analyze import run_local_assessment

        out = run_local_assessment(artifacts, report)
        print(f"[agent] Report written to: {out}")
        return

    try:
        load_runtime_settings()
    except SettingsLoadError as exc:
        raise SystemExit(str(exc)) from exc
    validate_llm_env()

    cursor_key = os.getenv("CURSOR_API_KEY", "").strip()
    openai_key = os.getenv("LLM_API_KEY", "").strip()

    if cursor_key:
        from agent.cursor_assess import run_cursor_assessment

        out = run_cursor_assessment(artifacts, report)
        print(f"[agent] Report written to: {out}")
        return

    if openai_key:
        from agent.agent import run_assessment
        from agent.config import get_settings

        settings = get_settings()
        out = run_assessment(artifacts, settings)
        if report is not None:
            dest = resolve_report_path(artifacts, report)
            if out.resolve() != dest:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"[agent] Report copied to: {dest}")
        print(f"[agent] Report written to: {out}")
        return

    raise SystemExit(
        "Could not start analysis because the .env credentials are empty.\n"
        "Set CURSOR_API_KEY or LLM_API_KEY and try again."
    )


if __name__ == "__main__":
    main()
