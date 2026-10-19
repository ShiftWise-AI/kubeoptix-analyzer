"""Load analyzer credentials from the platform System Settings API."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass(frozen=True)
class SystemSettings:
    language: str = ""
    cursor_api_key: str = ""
    cursor_model: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    status: str = ""
    default_extraction_method: str = ""


def _settings_base_url() -> str | None:
    url = os.getenv("SYSTEM_SETTINGS_URL", "").strip().rstrip("/")
    return url or None


def _is_container_or_ocp() -> bool:
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return True
    if Path("/.dockerenv").exists() or Path("/run/.containerenv").exists():
        return True
    return False


def _parse_settings(payload: dict) -> SystemSettings:
    return SystemSettings(
        language=str(payload.get("language") or "").strip(),
        cursor_api_key=str(payload.get("cursorApiKey") or "").strip(),
        cursor_model=str(payload.get("cursorModel") or "").strip(),
        llm_api_key=str(payload.get("llmApiKey") or "").strip(),
        llm_model=str(payload.get("llmModel") or "").strip(),
        status=str(payload.get("status") or "").strip().lower(),
        default_extraction_method=str(
            payload.get("defaultExtractionMethod") or ""
        ).strip().lower(),
    )


def fetch_system_settings(base_url: str) -> SystemSettings:
    timeout_s = float(os.getenv("SYSTEM_SETTINGS_TIMEOUT_S", "30"))
    url = f"{base_url.rstrip('/')}/system-settings"
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout_s) as client:
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.content.decode("utf-8", errors="replace").strip()
        detail = f": {body}" if body else ""
        if _is_container_or_ocp():
            raise SettingsLoadError(
                f"Failed to load system settings from {url} (HTTP {exc.response.status_code}){detail}"
            ) from exc
        print(
            f"[agent] Warning: system settings unavailable at {url} "
            f"(HTTP {exc.response.status_code}); using .env fallback."
        )
        return SystemSettings()
    except (httpx.RequestError, httpx.InvalidURL) as exc:
        if _is_container_or_ocp():
            raise SettingsLoadError(
                f"Failed to reach system settings API at {url}: {exc}"
            ) from exc
        print(
            f"[agent] Warning: system settings unreachable at {url} "
            f"({exc}); using .env fallback."
        )
        return SystemSettings()
    except json.JSONDecodeError as exc:
        if _is_container_or_ocp():
            raise SettingsLoadError(f"Invalid JSON from system settings API at {url}") from exc
        print(
            f"[agent] Warning: invalid JSON from system settings at {url}; "
            "using .env fallback."
        )
        return SystemSettings()

    if not isinstance(payload, dict):
        raise SettingsLoadError(f"Unexpected response from system settings API at {url}")

    return _parse_settings(payload)


def apply_system_settings(settings: SystemSettings) -> None:
    if settings.cursor_api_key:
        os.environ["CURSOR_API_KEY"] = settings.cursor_api_key
    if settings.cursor_model:
        os.environ["CURSOR_MODEL"] = settings.cursor_model
    if settings.llm_api_key:
        os.environ["LLM_API_KEY"] = settings.llm_api_key
    if settings.llm_model:
        os.environ["LLM_MODEL"] = settings.llm_model


class SettingsLoadError(RuntimeError):
    """Failed to load runtime settings from the platform API."""


def load_runtime_settings() -> bool:
    """Fetch platform settings, including the report language, before analysis."""
    from agent.i18n import UnsupportedLanguageError, set_report_language

    base_url = _settings_base_url()
    if not base_url:
        raise SettingsLoadError(
            "SYSTEM_SETTINGS_URL is required before report generation "
            "so the report language can be read from /system-settings."
        )

    settings = fetch_system_settings(base_url)
    if settings.status and settings.status != "active":
        raise SettingsLoadError(
            f"System settings status is '{settings.status}', expected 'active'."
        )

    try:
        code = set_report_language(settings.language)
    except UnsupportedLanguageError as exc:
        raise SettingsLoadError(str(exc)) from exc
    print(f"[agent] Report language: {code}")

    if not (
        settings.cursor_api_key
        or settings.cursor_model
        or settings.llm_api_key
        or settings.llm_model
    ):
        print(
            f"[agent] System settings at {base_url}/system-settings returned no credentials; "
            "using .env fallback."
        )
        return False

    apply_system_settings(settings)
    print(f"[agent] Loaded runtime settings from {base_url}/system-settings")
    if settings.cursor_api_key:
        print(
            f"[agent] Provider: Cursor SDK (model={settings.cursor_model or 'default'})"
        )
    elif settings.llm_api_key:
        print(
            f"[agent] Provider: OpenAI-compatible API "
            f"(model={settings.llm_model or 'default'})"
        )
    return True
