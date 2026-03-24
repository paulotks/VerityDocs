"""Load CLI strings and generator copy from YAML locale files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_LOCALES_DIR = Path(__file__).parent / "locales"

_cli_lang_override: str | None = None


def set_language(lang: str) -> None:
    """Optional default locale for future use (e.g. agent sessions)."""
    global _cli_lang_override
    _cli_lang_override = lang


def default_language() -> str:
    """Effective CLI locale after optional set_language; otherwise pt-BR."""
    return _cli_lang_override or "pt-BR"


def _normalize_lang(lang: str) -> str:
    return "en" if lang == "en" else "pt-BR"


@lru_cache(maxsize=8)
def _locale_payload(lang: str) -> dict[str, Any]:
    """lang is normalized: en or pt-BR."""
    path = _LOCALES_DIR / f"{lang}.yaml"
    if not path.is_file():
        path = _LOCALES_DIR / "pt-BR.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    return raw


def tr(lang: str, key: str, **kwargs: str) -> str:
    lang_n = _normalize_lang(lang)
    table = _locale_payload(lang_n)
    template = table.get(key)
    if template is None or not isinstance(template, str):
        fb = _locale_payload("pt-BR").get(key)
        template = fb if isinstance(fb, str) else None
    if template is None:
        return key
    return template.format(**kwargs)


def module_titles(language: str) -> list[str]:
    """Human-readable module titles aligned with PRD/SPEC file pairs."""
    lang_n = _normalize_lang(language)
    data = _locale_payload(lang_n)
    titles = data.get("module_titles")
    if isinstance(titles, list) and len(titles) > 0:
        return [str(x) for x in titles]
    fb = _locale_payload("pt-BR").get("module_titles")
    if isinstance(fb, list):
        return [str(x) for x in fb]
    return []


def docs_scaffold(language: str) -> dict[str, str]:
    """Stub markdown fragments for docs/ tree during init (traceability, flows, audit, etc.)."""
    lang_n = _normalize_lang(language)
    primary = _locale_payload(lang_n).get("docs_scaffold")
    fallback = _locale_payload("pt-BR").get("docs_scaffold")
    merged: dict[str, str] = {}
    if isinstance(fallback, dict):
        merged.update({str(k): str(v) for k, v in fallback.items()})
    if isinstance(primary, dict):
        merged.update({str(k): str(v) for k, v in primary.items()})
    return merged
