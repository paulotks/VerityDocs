"""Metadados padronizados em artefactos gerados (generatedBy / configHash) e parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path

from veritydocs import __version__

ARTIFACT_META_KEY = "_veritydocsArtifact"

ARTIFACT_META_HTML_RE = re.compile(
    r'<!--\s*VerityDocs\s+generatedBy="([^"]+)"\s+configHash="([a-f0-9]{64})"\s*-->\s*\n?',
)


def generated_by_value() -> str:
    return f"veritydocs/{__version__}"


def strip_artifact_metadata(relative_path: Path, content: str) -> str:
    """Remove metadados VerityDocs existentes para re-geração idempotente."""
    suffix = relative_path.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return content
        if isinstance(data, dict) and ARTIFACT_META_KEY in data:
            rest = {k: v for k, v in data.items() if k != ARTIFACT_META_KEY}
            return json.dumps(rest, indent=2, ensure_ascii=False).rstrip() + "\n"
        return content
    if suffix in (".md", ".mdc"):
        c = content.lstrip("\ufeff")
        m = ARTIFACT_META_HTML_RE.match(c)
        if m:
            return c[m.end() :]
        return content
    return content


def inject_artifact_metadata(relative_path: Path, content: str, config_hash: str) -> str:
    if not config_hash:
        return content
    body = strip_artifact_metadata(relative_path, content)
    gb = generated_by_value()
    suffix = relative_path.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return content
        if not isinstance(data, dict):
            return content
        merged = {
            ARTIFACT_META_KEY: {"generatedBy": gb, "configHash": config_hash},
            **data,
        }
        return json.dumps(merged, indent=2, ensure_ascii=False).rstrip() + "\n"
    if suffix in (".md", ".mdc"):
        header = f'<!-- VerityDocs generatedBy="{gb}" configHash="{config_hash}" -->\n'
        return header + body
    return body


def parse_embedded_meta(path: Path) -> tuple[str, str] | None:
    """Lê generatedBy e configHash embutidos; None se ausentes ou inválidos."""
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        art = data.get(ARTIFACT_META_KEY)
        if not isinstance(art, dict):
            return None
        gb = art.get("generatedBy")
        ch = art.get("configHash")
        if isinstance(gb, str) and isinstance(ch, str) and len(ch) == 64:
            return gb, ch
        return None
    c = text.lstrip("\ufeff")
    m = ARTIFACT_META_HTML_RE.match(c)
    if m:
        return m.group(1), m.group(2)
    return None
