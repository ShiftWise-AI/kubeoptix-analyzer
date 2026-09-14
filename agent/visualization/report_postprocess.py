"""Pós-processamento de relatórios Markdown (embed PNG + limpeza)."""

from __future__ import annotations

from pathlib import Path

from agent.visualization.pregenerate import (
    embedded_image_count,
    finalize_report_markdown,
    generate_all_visualizations,
)

_STRAY_SCRIPT_NAMES = frozenset({"generate_assets.py", "generate_charts.py", "render_assets.py"})


def cleanup_stray_report_scripts(report_dir: Path) -> list[str]:
    """Remove scripts .py criados pelo LLM no diretório de relatórios."""
    removed: list[str] = []
    if not report_dir.is_dir():
        return removed
    for path in report_dir.glob("*.py"):
        if path.name in _STRAY_SCRIPT_NAMES or path.name.startswith("generate_"):
            path.unlink(missing_ok=True)
            removed.append(path.name)
    return removed


def postprocess_report_file(
    report_file: Path,
    artifacts_dir: Path,
) -> dict[str, int | list[str]]:
    """Embute PNGs como base64 no .md e remove scripts espúrios do diretório de reports."""
    report_file = report_file.resolve()
    artifacts_dir = artifacts_dir.resolve()
    report_dir = report_file.parent

    if not report_file.is_file():
        return {"embedded": 0, "removed_scripts": []}

    _, visualizations = generate_all_visualizations(artifacts_dir)
    content = report_file.read_text(encoding="utf-8")
    final = finalize_report_markdown(
        content,
        artifacts_dir=artifacts_dir,
        report_dir=report_dir,
        visualizations=visualizations,
    )
    report_file.write_text(final, encoding="utf-8")
    removed = cleanup_stray_report_scripts(report_dir)

    return {
        "embedded": embedded_image_count(final),
        "removed_scripts": removed,
    }
