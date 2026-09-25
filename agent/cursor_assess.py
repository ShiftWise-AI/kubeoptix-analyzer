"""Assessment via Cursor SDK (subscription CURSOR_API_KEY)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

_CURSOR_MODEL_ALIASES = {
    "deafult": "default",
}


def _initialize_progress_file(progress_path: str) -> None:
    if not progress_path:
        return
    target = Path(progress_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        '{"current_file": null, "processed_files": []}',
        encoding="utf-8",
    )
    temporary.replace(target)


def run_cursor_assessment(
    artifacts_dir: Path,
    report_path: Path | None = None,
) -> Path:
    try:
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions
    except ImportError as exc:
        raise SystemExit(
            "cursor-sdk package is not installed. Run:\n"
            "  pip install cursor-sdk\n"
        ) from exc

    from agent.local_analyze import resolve_report_path
    from agent.prompts import build_cursor_prompt
    from agent.visualization.pregenerate import (
        finalize_report_markdown,
        format_visualization_catalog,
        generate_all_visualizations,
    )

    artifacts_dir = artifacts_dir.resolve()
    if not artifacts_dir.is_dir():
        raise SystemExit(f"Invalid artifacts directory: {artifacts_dir}")

    api_key = os.getenv("CURSOR_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "CURSOR_API_KEY is not set. Configure SYSTEM_SETTINGS_URL or .env "
            "(https://cursor.com/dashboard/api)."
        )

    out = resolve_report_path(artifacts_dir, report_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    assets, visualizations = generate_all_visualizations(artifacts_dir)
    viz_catalog = format_visualization_catalog(visualizations)
    if visualizations:
        print(
            f"[agent] Pre-generated {len(visualizations)} namespace visualization set(s) "
            f"in {assets.assets_dir}"
        )

    raw_model = os.getenv("CURSOR_MODEL", "composer-2.5").strip() or "composer-2.5"
    model = _CURSOR_MODEL_ALIASES.get(raw_model.lower(), raw_model)
    if model != raw_model:
        print(f"[agent] Warning: normalized CURSOR_MODEL={raw_model!r} to {model!r}")
    progress_path = os.getenv("KUBEOPTIX_PROGRESS_FILE", "").strip()
    _initialize_progress_file(progress_path)
    prompt = build_cursor_prompt(str(out), progress_path=progress_path)
    if viz_catalog.strip():
        from agent.i18n import t

        prompt = f"{prompt}\n\n{t('viz.cursor_note')}\n\n{viz_catalog}\n"

    print(f"[agent] LLM mode via Cursor SDK")
    print(f"[agent] Artifacts (cwd): {artifacts_dir}")
    print(f"[agent] Model: {model}")
    print(f"[agent] Target report: {out}")

    result = Agent.prompt(
        prompt,
        AgentOptions(
            api_key=api_key,
            model=model,
            local=LocalAgentOptions(cwd=str(artifacts_dir)),
        ),
    )

    status = getattr(result, "status", None)
    text = getattr(result, "result", None) or ""
    print(f"[agent] Cursor status: {status}")
    if text:
        preview = str(text).strip()
        if len(preview) > 400:
            preview = preview[:400] + "..."
        print(f"[agent] Summary: {preview}")

    if not out.is_file():
        # Fallback: if the agent returned only text, write it ourselves.
        if text and str(text).strip():
            out.write_text(str(text).strip() + "\n", encoding="utf-8")
            print(f"[agent] Report written from model output: {out}")
        else:
            raise SystemExit(
                f"The Cursor agent finished without creating the file: {out}\n"
                f"Status: {status}"
            )
    else:
        print(f"[agent] Report generated at: {out}")

    content = out.read_text(encoding="utf-8")
    final = finalize_report_markdown(
        content,
        artifacts_dir=artifacts_dir,
        report_dir=out.parent,
        visualizations=visualizations,
    )
    out.write_text(final, encoding="utf-8")
    embedded_count = final.count("data:image/png;base64,")
    print(f"[agent] Embedded {embedded_count} PNG image(s) into report body")

    from agent.visualization.report_postprocess import cleanup_stray_report_scripts

    cleanup_stray_report_scripts(out.parent)
    return out
