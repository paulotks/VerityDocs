from __future__ import annotations

import logging
from pathlib import Path

from veritydocs.toolgen.artifact_metadata import inject_artifact_metadata
from veritydocs.toolgen.context import GeneratedFile, GenerationContext
from veritydocs.toolgen.registry import get_adapter

LOGGER = logging.getLogger("veritydocs.toolgen")


def _materialize(
    project_dir: Path,
    files: list[GeneratedFile],
    ctx: GenerationContext,
) -> list[Path]:
    written: list[Path] = []
    for gf in files:
        path = project_dir / gf.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = gf.content.rstrip() + "\n"
        body = inject_artifact_metadata(gf.relative_path, raw, ctx.config_hash)
        path.write_text(body.rstrip() + "\n", encoding="utf-8")
        written.append(path)
    return written


def generate_tool_artifacts(ctx: GenerationContext, tools: list[str]) -> list[Path]:
    created: list[Path] = []
    for tid in tools:
        adapter = get_adapter(tid)
        if adapter is None:
            LOGGER.warning("Sem adaptador VerityDocs para a ferramenta '%s'; ignorada.", tid)
            continue
        batches: list[GeneratedFile] = [
            *adapter.generate_rules(ctx),
            *adapter.generate_workflows(ctx),
            *adapter.generate_skills(ctx),
            *adapter.generate_mcp_config(ctx),
        ]
        created.extend(_materialize(ctx.project_dir, batches, ctx))
    return created
