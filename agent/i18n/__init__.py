"""Report language loaded from system settings.

Translations are keyed by message id and then by language code
(``pt-br``, ``en-us``, ``es``, ``it``). Call ``set_report_language`` after
reading ``/system-settings`` and before any report text is built.
"""

from __future__ import annotations

from contextvars import ContextVar

from agent.i18n.catalog import MESSAGES as _CATALOG_MESSAGES
from agent.i18n.prompts import PROMPT_MESSAGES

SUPPORTED_LANGUAGES: tuple[str, ...] = ("pt-br", "en-us", "es", "it")

# Short / alternate codes returned by system settings UI.
_LANGUAGE_ALIASES: dict[str, str] = {
    "en": "en-us",
    "en_us": "en-us",
    "eng": "en-us",
    "pt": "pt-br",
    "pt_br": "pt-br",
    "por": "pt-br",
    "es_es": "es",
    "spa": "es",
    "it_it": "it",
    "ita": "it",
}

MESSAGES: dict[str, dict[str, str]] = {**_CATALOG_MESSAGES, **PROMPT_MESSAGES}

_language: ContextVar[str | None] = ContextVar("report_language", default=None)


class UnsupportedLanguageError(ValueError):
    """``language`` from system settings is missing or not supported."""

    def __init__(self, language: str) -> None:
        self.language = language
        supported = ", ".join(SUPPORTED_LANGUAGES)
        shown = language.strip() or "(empty)"
        super().__init__(
            f"Invalid or missing system settings language {shown!r}. "
            f"Expected one of: {supported}."
        )


def _validate_catalog() -> None:
    for key, translations in MESSAGES.items():
        missing = [
            code
            for code in SUPPORTED_LANGUAGES
            if not str(translations.get(code, "")).strip()
        ]
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Translation {key!r} is missing: {joined}")


_validate_catalog()


def normalize_language(language: str) -> str:
    raw = (language or "").strip().lower()
    code = raw.replace("_", "-")
    code = _LANGUAGE_ALIASES.get(raw, _LANGUAGE_ALIASES.get(code, code))
    if code not in SUPPORTED_LANGUAGES:
        raise UnsupportedLanguageError(language)
    return code


def set_report_language(language: str) -> str:
    """Activate the report language. Raises if the code is not supported."""
    code = normalize_language(language)
    _language.set(code)
    return code


def clear_report_language() -> None:
    _language.set(None)


def get_report_language() -> str:
    code = _language.get()
    if not code:
        raise UnsupportedLanguageError("")
    return code


def t(key: str, **kwargs: object) -> str:
    """Return ``key`` in the active report language."""
    lang = get_report_language()
    try:
        template = MESSAGES[key][lang]
    except KeyError as exc:
        raise KeyError(f"Missing translation {key!r} for {lang}") from exc
    if kwargs:
        return template.format(**kwargs)
    return template


def yn(value: bool) -> str:
    return t("yes") if value else t("no")


def severity_label(code: str) -> str:
    return t(f"severity.{code}")
