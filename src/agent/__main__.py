"""CLI: PYTHONPATH=src python -m agent --artifacts ./pasta [--mode local|llm]."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from agent.local_analyze import resolve_report_path, run_local_assessment

_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assessment OpenShift: análise local ou LLM (Cursor SDK / OpenAI-compatible)."
    )
    parser.add_argument(
        "--artifacts",
        "-a",
        required=True,
        help="Diretório com artefatos coletados",
    )
    parser.add_argument(
        "--report",
        "-r",
        default=None,
        help=(
            "Arquivo .md ou diretório de saída "
            "(default: <artifacts>/assessment-report.md)"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("local", "llm"),
        default="local",
        help=(
            "local = heurísticas sem LLM; "
            "llm = Cursor SDK (CURSOR_API_KEY) ou API OpenAI-compatible (LLM_API_KEY)"
        ),
    )
    args = parser.parse_args()

    artifacts = Path(args.artifacts)
    report = Path(args.report) if args.report else None

    if args.mode == "local":
        out = run_local_assessment(artifacts, report)
        print(f"[agent] Relatório gravado em: {out}")
        return

    cursor_key = os.getenv("CURSOR_API_KEY", "").strip()
    openai_key = os.getenv("LLM_API_KEY", "").strip()

    if cursor_key:
        from agent.cursor_assess import run_cursor_assessment

        out = run_cursor_assessment(artifacts, report)
        print(f"[agent] Relatório gravado em: {out}")
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
                print(f"[agent] Relatório copiado para: {dest}")
        print(f"[agent] Relatório gravado em: {out}")
        return

    raise SystemExit(
        "Para --mode llm configure CURSOR_API_KEY (assinatura Cursor) "
        "ou LLM_API_KEY (API OpenAI-compatible) no .env.\n"
        "Veja .env.example."
    )


if __name__ == "__main__":
    main()
