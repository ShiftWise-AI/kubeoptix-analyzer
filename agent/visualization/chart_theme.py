"""Paleta e utilitários compartilhados entre gráficos do relatório."""

from __future__ import annotations

CHART_COLORS: tuple[str, ...] = (
    "#004B95",
    "#38812F",
    "#005F60",
    "#3C3D99",
    "#C58C00",
    "#C46100",
    "#A30000",
    "#4D4D4D",
    "#002F5D",
    "#23511E",
    "#003737",
    "#2A265F",
)

CHART_MUTED_COLOR = "#6A6E73"
CHART_MAX_WIDTH = 720


def format_chart_value(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"


def format_chart_percent(value: float, total: float) -> str:
    if total <= 0:
        return "0%"
    pct = (value / total) * 100
    if pct == int(pct):
        return f"{int(pct)}%"
    return f"{pct:.1f}%"
