"""System prompts for the OCP assessment agent."""

from __future__ import annotations

from agent.i18n import t


def build_system_prompt() -> str:
    return t("prompt.system")


def build_cursor_prompt(report_path: str, progress_path: str = "") -> str:
    prompt = t("prompt.cursor", report_path=report_path)
    if not progress_path:
        return prompt

    return (
        f"{prompt}\n\n"
        "Acompanhe o progresso no arquivo JSON abaixo. Depois de ler cada arquivo "
        "de artefato, atualize-o atomicamente (escreva um .tmp e renomeie) com este "
        "formato: {\"current_file\": \"caminho relativo\", "
        "\"processed_files\": [\"caminho relativo\", ...]}. Inclua somente arquivos "
        "que realmente foram lidos e mantenha a lista acumulada. Antes de iniciar, "
        "grave current_file como null e processed_files como []. Não marque o "
        "relatório final nem arquivos temporários como processados.\n"
        f"Arquivo de progresso: {progress_path}"
    )


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
