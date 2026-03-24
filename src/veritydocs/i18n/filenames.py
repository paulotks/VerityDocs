"""Logical doc filenames per locale (filemap under scaffold templates)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DOCS_ROOT = Path(__file__).resolve().parent.parent / "scaffold" / "templates" / "docs"


def normalize_docs_locale(language: str) -> str:
    """Map project language flag to template locale directory name."""
    return "en" if language == "en" else "pt-BR"


def load_docs_filemap(locale: str) -> dict[str, dict[str, str]]:
    """
    Load PRD/SPEC filename map for a template locale (`en` or `pt-BR`).
    Keys: prd, spec — each maps logical template keys to output filenames.
    """
    path = _DOCS_ROOT / locale / "filemap.yaml"
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = "filemap.yaml invalido"
        raise ValueError(msg)
    prd = raw.get("prd")
    spec = raw.get("spec")
    if not isinstance(prd, dict) or not isinstance(spec, dict):
        msg = "filemap.yaml deve conter chaves prd e spec"
        raise ValueError(msg)
    prd_map = {str(k): str(v) for k, v in prd.items()}
    spec_map = {str(k): str(v) for k, v in spec.items()}
    return {"prd": prd_map, "spec": spec_map}


def docs_templates_dir(locale: str) -> Path:
    """Directory containing Jinja templates for `locale` (en or pt-BR)."""
    return _DOCS_ROOT / locale
