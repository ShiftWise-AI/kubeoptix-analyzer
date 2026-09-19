"""References section of the assessment report."""

from __future__ import annotations

from agent.i18n import t


def render_references_md() -> str:
    return t("references.body")
