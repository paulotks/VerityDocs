"""Esquema de metadata.yaml para mudanças documentais."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

CHANGE_TYPES = (
    "requirement",
    "architecture",
    "flow",
    "criteria",
    "decision",
    "restructure",
    "stack",
)

ChangeType = Literal[
    "requirement",
    "architecture",
    "flow",
    "criteria",
    "decision",
    "restructure",
    "stack",
]

ChangeStatus = Literal["draft", "applied", "archived"]


class ChangeMetadata(BaseModel):
    """Conteúdo canónico de `docs/changes/<slug>/metadata.yaml`."""

    version: str = "1"
    change_type: ChangeType = "requirement"
    status: ChangeStatus = "draft"
    created_at: str
    updated_at: str
    author: str = ""
    tool: str = ""
    skill_evolution: bool = False
    summary: str = ""
    archived_at: str | None = None
    archive_relative_path: str | None = None
    original_slug: str | None = None
