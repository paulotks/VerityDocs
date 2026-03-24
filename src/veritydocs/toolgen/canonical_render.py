"""Renderização de templates canónicos (skills + workflows) para toolgen."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from veritydocs.skill_evolution import (
    CONTEXT7_MCP_QUERY_DOCS_TOOL,
    CONTEXT7_MCP_RESOLVE_LIBRARY_TOOL,
)
from veritydocs.toolgen.context import GenerationContext

_CANONICAL_ROOT = Path(__file__).parent / "templates" / "canonical"

CANONICAL_SKILL_IDS: tuple[str, ...] = (
    "context-only-docs",
    "docs-audit-consistency",
    "mermaid-flows",
    "traceability-update",
    "decision-capture",
    "skill-evolution",
)

CANONICAL_WORKFLOW_IDS: tuple[str, ...] = (
    "propose",
    "explore",
    "apply",
    "archive",
    "verify",
    "sync",
    "onboard",
    "lang",
)


@lru_cache(maxsize=1)
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(_CANONICAL_ROOT.as_posix()),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )


def _template_vars(ctx: GenerationContext) -> dict[str, object]:
    return {
        "project_name": ctx.project_name,
        "language": ctx.language,
        "domain": ctx.domain,
        "profile": ctx.profile,
        "is_en": ctx.language == "en",
        "docs_root": "docs",
        "resolve_tool": CONTEXT7_MCP_RESOLVE_LIBRARY_TOOL,
        "query_tool": CONTEXT7_MCP_QUERY_DOCS_TOOL,
    }


def render_skill_body(skill_id: str, ctx: GenerationContext) -> str:
    if skill_id not in CANONICAL_SKILL_IDS:
        msg = f"Skill canónico desconhecido: {skill_id!r}"
        raise ValueError(msg)
    tpl = _environment().get_template(f"skills/{skill_id}.md.j2")
    return tpl.render(**_template_vars(ctx)).strip()


def render_workflow_body(workflow_id: str, ctx: GenerationContext) -> str:
    if workflow_id not in CANONICAL_WORKFLOW_IDS:
        msg = f"Workflow canónico desconhecido: {workflow_id!r}"
        raise ValueError(msg)
    tpl = _environment().get_template(f"workflows/{workflow_id}.md.j2")
    return tpl.render(**_template_vars(ctx)).strip()
