from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GenerationContext:
    project_dir: Path
    project_name: str
    language: str
    domain: str
    profile: str
    # Hash estável da config (`compute_config_hash`); vazio omite cabeçalhos nos artefactos.
    config_hash: str = ""


@dataclass(frozen=True)
class GeneratedFile:
    """Artefato lógico a gravar sob `project_dir` (caminho relativo à raiz do projeto)."""

    relative_path: Path
    content: str
