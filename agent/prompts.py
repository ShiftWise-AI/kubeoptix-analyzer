"""System prompts for the OCP assessment agent."""

from __future__ import annotations

from agent.i18n import t


def build_system_prompt() -> str:
    return t("prompt.system")


def build_cursor_prompt(report_path: str) -> str:
    return t("prompt.cursor", report_path=report_path)


def build_user_prompt(
    artifacts_dir: str,
    inventory: str,
    visualization_catalog: str = "",
) -> str:
    viz_block = ""
    if visualization_catalog.strip():
        viz_block = (
            f"\n\n{t('prompt.viz_preface')}\n"
            f"{visualization_catalog}\n"
        )
    return (
        f"{t('prompt.user_artifacts', path=artifacts_dir)}\n\n"
        f"{t('prompt.user_inventory')}\n{inventory}\n"
        f"{viz_block}\n"
        f"{t('prompt.user_closing')}"
    )
