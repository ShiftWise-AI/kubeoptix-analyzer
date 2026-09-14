"""CLI: python -m agent --artifacts ./folder [--report path] [--llm]."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from agent.config import validate_llm_env
from agent.system_settings import SettingsLoadError, load_runtime_settings

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def _report_stats(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    embedded = content.count("data:image/png;base64,")
    relative = len(re.findall(r"!\[[^\]]*\]\([^)]*report_assets[^)]*\)", content))
    print(f"[agent] Report written to: {path}")
    print(f"[agent] Embedded {embedded} PNG image(s) in markdown body")
    if relative:
        print(f"[agent] Warning: {relative} unembedded image reference(s) remain")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "OpenShift assessment via Cursor SDK or OpenAI-compatible LLM (ReAct + tools)."
        )
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
        "--llm",
        action="store_true",
        help="Force OpenAI-compatible LLM API (requires LLM_API_KEY)",
    )
    args = parser.parse_args()

    artifacts = Path(args.artifacts)
    report = Path(args.report) if args.report else None

    try:
        load_runtime_settings()
    except SettingsLoadError as exc:
        raise SystemExit(str(exc)) from exc
    validate_llm_env()

    cursor_key = os.getenv("CURSOR_API_KEY", "").strip()
    openai_key = os.getenv("LLM_API_KEY", "").strip()

    if args.llm:
        if not openai_key:
            raise SystemExit(
                "--llm requires LLM_API_KEY (configure via SYSTEM_SETTINGS_URL or .env)."
            )
        from agent.agent import run_assessment
        from agent.config import get_settings

        settings = get_settings()
        print("[agent] Provider: OpenAI-compatible API (--llm)")
        print(f"[agent] Model: {settings.llm_model}")
        out = run_assessment(artifacts, settings, report_path=report)
        _report_stats(out)
        return

    if cursor_key:
        from agent.cursor_assess import run_cursor_assessment

        out = run_cursor_assessment(artifacts, report)
        _report_stats(out)
        return

    if openai_key:
        from agent.agent import run_assessment
        from agent.config import get_settings

        settings = get_settings()
        print("[agent] Provider: OpenAI-compatible API")
        print(f"[agent] Model: {settings.llm_model}")
        out = run_assessment(artifacts, settings, report_path=report)
        _report_stats(out)
        return

    raise SystemExit(
        "Could not start analysis: no credentials available.\n"
        "Configure CURSOR_API_KEY or LLM_API_KEY via system settings or .env."
    )


if __name__ == "__main__":
    main()
