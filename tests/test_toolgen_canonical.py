"""Smoke tests for canonical skill/workflow Jinja templates."""

from __future__ import annotations

from pathlib import Path

import pytest

from veritydocs.toolgen.canonical_render import (
    CANONICAL_SKILL_IDS,
    CANONICAL_WORKFLOW_IDS,
    render_skill_body,
    render_workflow_body,
)
from veritydocs.toolgen.context import GenerationContext


def _ctx(*, lang: str) -> GenerationContext:
    return GenerationContext(
        project_dir=Path("."),
        project_name="TestProj",
        language=lang,
        domain="software",
        profile="core",
    )


@pytest.mark.parametrize("skill_id", CANONICAL_SKILL_IDS)
@pytest.mark.parametrize("lang", ("en", "pt-BR"))
def test_render_all_skills(skill_id: str, lang: str) -> None:
    body = render_skill_body(skill_id, _ctx(lang=lang))
    assert f"# {skill_id}" in body
    assert len(body) > 80


@pytest.mark.parametrize("workflow_id", CANONICAL_WORKFLOW_IDS)
@pytest.mark.parametrize("lang", ("en", "pt-BR"))
def test_render_all_workflows(workflow_id: str, lang: str) -> None:
    body = render_workflow_body(workflow_id, _ctx(lang=lang))
    assert f"# vrtdocs:{workflow_id}" in body
    assert len(body) > 80
