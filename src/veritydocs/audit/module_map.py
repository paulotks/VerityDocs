from __future__ import annotations

import json
from pathlib import Path

from veritydocs.config import ModuleMapping


def load_module_mapping(path: Path) -> list[ModuleMapping]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [ModuleMapping.model_validate(m) for m in raw.get("modules", [])]


def validate_mapping_files(docs_root: Path, modules: list[ModuleMapping]) -> list[str]:
    errors: list[str] = []
    for mod in modules:
        all_paths = [mod.prd_path, *mod.spec_primary, *[s.path for s in mod.spec_secondary]]
        for rel in all_paths:
            if not (docs_root.parent / rel).exists():
                errors.append(f"{mod.module_id}: caminho inexistente {rel}")
    return errors
