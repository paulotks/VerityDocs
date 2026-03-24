"""Criação de change folders, metadata.yaml e ciclo draft → applied → archived."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from veritydocs.change_manager.models import CHANGE_TYPES, ChangeMetadata

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG_LEN = 120


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def validate_slug(slug: str) -> None:
    if not slug or len(slug) > MAX_SLUG_LEN:
        msg = f"Slug invalido (vazio ou > {MAX_SLUG_LEN} caracteres)."
        raise ValueError(msg)
    if slug in ("archive", ".", "..") or "/" in slug or "\\" in slug:
        msg = "Slug invalido (reservado ou contem separadores)."
        raise ValueError(msg)
    if not SLUG_RE.match(slug):
        msg = "Slug deve ser kebab-case (ex.: tactical-ddd, billing-api)."
        raise ValueError(msg)


def resolve_changes_dir(project_root: Path, docs_root: str) -> Path:
    return (project_root / docs_root.strip("/").replace("\\", "/") / "changes").resolve()


def read_metadata(change_dir: Path) -> dict[str, Any] | None:
    meta = change_dir / "metadata.yaml"
    if not meta.is_file():
        return None
    try:
        raw = yaml.safe_load(meta.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {"_error": "invalid_yaml"}
    return raw if isinstance(raw, dict) else None


def write_metadata(change_dir: Path, data: ChangeMetadata) -> Path:
    path = change_dir / "metadata.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = data.model_dump(mode="json", exclude_none=True)
    path.write_text(
        yaml.safe_dump(
            payload,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def parse_metadata_dict(raw: dict[str, Any]) -> ChangeMetadata | None:
    if "_error" in raw:
        return None
    try:
        return ChangeMetadata.model_validate(raw)
    except ValidationError:
        return None


def list_open_change_dirs(changes_dir: Path) -> list[Path]:
    if not changes_dir.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(changes_dir.iterdir()):
        if p.is_dir() and p.name != "archive" and not p.name.startswith("."):
            out.append(p)
    return out


@dataclass
class CreateChangeResult:
    slug: str
    change_dir: Path
    files: list[Path]


def _stub_files(lang: str) -> tuple[str, str, str]:
    from veritydocs.i18n import tr

    return (
        tr(lang, "change_stub_proposal"),
        tr(lang, "change_stub_design"),
        tr(lang, "change_stub_tasks"),
    )


def create_change(
    project_root: Path,
    docs_root: str,
    slug: str,
    *,
    change_type: str,
    author: str = "",
    tool: str = "",
    summary: str = "",
    skill_evolution: bool = False,
    language: str = "pt-BR",
    force: bool = False,
) -> CreateChangeResult:
    validate_slug(slug)
    if change_type not in CHANGE_TYPES:
        valid = ", ".join(CHANGE_TYPES)
        msg = f"Tipo invalido {change_type!r}. Use: {valid}"
        raise ValueError(msg)

    changes_dir = resolve_changes_dir(project_root, docs_root)
    change_dir = changes_dir / slug
    if change_dir.exists():
        if not force:
            msg = f"Ja existe um change em {change_dir.as_posix()} (use --force para recriar)."
            raise FileExistsError(msg)
        shutil.rmtree(change_dir)

    ts = now_iso()
    meta = ChangeMetadata.model_validate(
        {
            "change_type": change_type,
            "status": "draft",
            "created_at": ts,
            "updated_at": ts,
            "author": author,
            "tool": tool,
            "summary": summary,
            "skill_evolution": skill_evolution,
        }
    )
    proposal, design, tasks = _stub_files(language)

    change_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for rel, body in (
        ("proposal.md", proposal),
        ("design.md", design),
        ("tasks.md", tasks),
    ):
        p = change_dir / rel
        p.write_text(body.rstrip() + "\n", encoding="utf-8")
        files.append(p)
    files.append(write_metadata(change_dir, meta))
    return CreateChangeResult(slug=slug, change_dir=change_dir, files=files)


def mark_applied(project_root: Path, docs_root: str, slug: str) -> ChangeMetadata:
    validate_slug(slug)
    changes_dir = resolve_changes_dir(project_root, docs_root)
    change_dir = changes_dir / slug
    if not change_dir.is_dir():
        msg = f"Change nao encontrado: {change_dir.as_posix()}"
        raise FileNotFoundError(msg)
    raw = read_metadata(change_dir)
    if raw is None:
        msg = "metadata.yaml em falta ou invalido."
        raise ValueError(msg)
    meta = parse_metadata_dict(raw)
    if meta is None:
        msg = "metadata.yaml nao segue o esquema esperado."
        raise ValueError(msg)
    if meta.status != "draft":
        msg = f"Transicao invalida: status actual e {meta.status!r} (esperado draft)."
        raise ValueError(msg)
    ts = now_iso()
    updated = meta.model_copy(update={"status": "applied", "updated_at": ts})
    write_metadata(change_dir, updated)
    return updated


def _append_archive_readme(
    changes_dir: Path,
    *,
    date_str: str,
    slug: str,
    summary: str,
    lang: str,
) -> Path | None:
    readme = changes_dir / "README.md"
    if not readme.is_file():
        return None
    from veritydocs.i18n import tr

    line = tr(
        lang,
        "change_readme_archive_line",
        date=date_str,
        slug=slug,
        summary=summary or "—",
    )
    text = readme.read_text(encoding="utf-8").rstrip()
    header = tr(lang, "change_readme_archive_header")
    if header not in text:
        text = f"{text}\n\n{header}\n"
    text = f"{text}\n{line}\n"
    readme.write_text(text, encoding="utf-8")
    return readme


def archive_change(
    project_root: Path,
    docs_root: str,
    slug: str,
    *,
    force: bool = False,
    readme_summary: str = "",
    language: str = "pt-BR",
) -> Path:
    """Move o change para `archive/YYYY-MM-DD-<slug>/` e actualiza metadata."""

    validate_slug(slug)
    changes_dir = resolve_changes_dir(project_root, docs_root)
    change_dir = changes_dir / slug
    if not change_dir.is_dir():
        msg = f"Change nao encontrado: {change_dir.as_posix()}"
        raise FileNotFoundError(msg)
    raw = read_metadata(change_dir)
    if raw is None:
        msg = "metadata.yaml em falta ou invalido."
        raise ValueError(msg)
    meta = parse_metadata_dict(raw)
    if meta is None:
        msg = "metadata.yaml nao segue o esquema esperado."
        raise ValueError(msg)
    if meta.status != "applied" and not force:
        msg = (
            "Apenas changes com status applied podem ser arquivados "
            "(use --force para arquivar a partir de outro estado)."
        )
        raise ValueError(msg)

    archive_root = changes_dir / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    dest_name = f"{date_str}-{slug}"
    dest = archive_root / dest_name
    if dest.exists():
        msg = f"Destino ja existe: {dest.as_posix()}"
        raise FileExistsError(msg)

    shutil.move(str(change_dir), str(dest))

    ts = now_iso()
    rel = f"{docs_root.strip('/').replace(chr(92), '/')}/changes/archive/{dest_name}"
    updated = meta.model_copy(
        update={
            "status": "archived",
            "updated_at": ts,
            "archived_at": ts,
            "archive_relative_path": rel,
            "original_slug": slug,
            "summary": readme_summary or meta.summary,
        }
    )
    write_metadata(dest, updated)
    summ = readme_summary or meta.summary
    _append_archive_readme(changes_dir, date_str=date_str, slug=slug, summary=summ, lang=language)
    return dest
