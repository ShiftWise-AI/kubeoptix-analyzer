"""CLI: python -m agent --llm --artifacts ./folder [--report path]."""

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenShift assessment via OpenAI-compatible LLM (ReAct + tools)."
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
        required=True,
        help="Run assessment with OpenAI-compatible LLM API",
    )
    args = parser.parse_args()

    artifacts = Path(args.artifacts)
    report = Path(args.report) if args.report else None

    try:
        load_runtime_settings()
    except SettingsLoadError as exc:
        raise SystemExit(str(exc)) from exc
    validate_llm_env()

    openai_key = os.getenv("LLM_API_KEY", "").strip()
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

    content = out.read_text(encoding="utf-8")
    embedded = content.count("data:image/png;base64,")
    relative = len(re.findall(r"!\[[^\]]*\]\([^)]*report_assets[^)]*\)", content))
    print(f"[agent] Report written to: {out}")
    print(f"[agent] Embedded {embedded} PNG image(s) in markdown body")
    if relative:
        print(f"[agent] Warning: {relative} unembedded image reference(s) remain")


if __name__ == "__main__":
    main()
