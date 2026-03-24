"""Tests for toolgen: registry, adapters, generate_tool_artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from veritydocs.config import compute_config_hash
from veritydocs.toolgen.adapters import ClaudeAdapter, CursorAdapter
from veritydocs.toolgen.artifact_metadata import ARTIFACT_META_KEY, parse_embedded_meta
from veritydocs.toolgen.context import GenerationContext
from veritydocs.toolgen.generator import generate_tool_artifacts
from veritydocs.toolgen.registry import (
    adapters_snapshot,
    get_adapter,
    list_adapter_ids,
    register_adapter,
)


def _ctx(project_dir: Path, *, lang: str = "pt-BR", config_hash: str = "") -> GenerationContext:
    return GenerationContext(
        project_dir=project_dir,
        project_name="P",
        language=lang,
        domain="software",
        profile="core",
        config_hash=config_hash,
    )


def test_list_adapter_ids_sorted() -> None:
    ids = list_adapter_ids()
    assert ids == tuple(sorted(ids))
    assert "cursor" in ids and "claude" in ids


def test_get_adapter_case_insensitive() -> None:
    assert get_adapter("CURSOR") is not None
    assert get_adapter("unknown-tool") is None


def test_register_adapter_duplicate_raises() -> None:
    snap = adapters_snapshot()
    try:
        with pytest.raises(ValueError, match="já registado"):
            register_adapter(snap["cursor"], override=False)
    finally:
        pass


def test_register_adapter_override_restores() -> None:
    snap = adapters_snapshot()
    original = snap["cursor"]

    class StubCursor:
        tool_id = "cursor"
        display_name = "Stub"
        detect_paths = ()

        def detect_existing(self, project_dir: Path) -> bool:
            return False

        def generate_rules(self, ctx: GenerationContext):
            return []

        def generate_workflows(self, ctx: GenerationContext):
            return []

        def generate_skills(self, ctx: GenerationContext):
            return []

        def generate_mcp_config(self, ctx: GenerationContext):
            return []

    register_adapter(StubCursor(), override=True)
    try:
        assert isinstance(get_adapter("cursor"), StubCursor)
    finally:
        register_adapter(original, override=True)
    assert isinstance(get_adapter("cursor"), CursorAdapter)


def test_cursor_adapter_detect_existing(tmp_path: Path) -> None:
    ad = CursorAdapter()
    assert ad.detect_existing(tmp_path) is False
    (tmp_path / ".cursor").mkdir()
    assert ad.detect_existing(tmp_path) is True


def test_claude_adapter_injects_block_in_existing_claude_md(tmp_path: Path) -> None:
    ad = ClaudeAdapter()
    (tmp_path / "CLAUDE.md").write_text("# Title\n\nSome text.\n", encoding="utf-8")
    ctx = _ctx(tmp_path, lang="en")
    files = ad.generate_rules(ctx)
    assert len(files) == 1
    assert files[0].relative_path == Path("CLAUDE.md")
    assert "veritydocs:start" in files[0].content
    assert "Some text." in files[0].content
    # Second run replaces the block
    files2 = ad.generate_rules(ctx)
    assert files2[0].content.count("veritydocs:start") == 1


def test_claude_adapter_skills_count(tmp_path: Path) -> None:
    ad = ClaudeAdapter()
    ctx = _ctx(tmp_path, lang="en")
    skills = ad.generate_skills(ctx)
    assert len(skills) == 6
    assert all(p.relative_path.parts[:2] == (".claude", "skills") for p in skills)


def test_cursor_mcp_json_valid(tmp_path: Path) -> None:
    ad = CursorAdapter()
    ctx = _ctx(tmp_path)
    mcp = ad.generate_mcp_config(ctx)
    assert len(mcp) == 1
    data = json.loads(mcp[0].content)
    assert "mcpServers" in data


def test_generate_tool_artifacts_cursor_writes_files(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    paths = generate_tool_artifacts(ctx, ["cursor"])
    assert paths
    assert (tmp_path / ".cursor" / "rules" / "veritydocs-core.mdc").is_file()
    assert (tmp_path / ".cursor" / "commands" / "vrtdocs-propose.md").is_file()


def test_generate_tool_artifacts_unknown_tool_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        out = generate_tool_artifacts(ctx, ["not-a-real-adapter"])
    assert out == []
    assert "Sem adaptador" in caplog.text


def test_generate_tool_artifacts_cursor_and_claude(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, lang="en")
    paths = generate_tool_artifacts(ctx, ["cursor", "claude"])
    rels = {p.resolve().relative_to(tmp_path) for p in paths}
    assert Path(".cursor/rules/veritydocs-core.mdc") in rels
    assert Path("CLAUDE.md") in rels
    assert any(p.parts[:2] == (".claude", "skills") for p in rels)


def test_generate_tool_artifacts_embeds_config_hash(tmp_path: Path) -> None:
    cfg = tmp_path / "veritydocs.config.yaml"
    cfg.write_text(
        "version: '1.0'\n"
        "project:\n  name: T\n  language: pt-BR\n  domain: software\n"
        "docs_root: docs\n"
        "tools: [cursor]\n",
        encoding="utf-8",
    )
    h = compute_config_hash(cfg)
    ctx = _ctx(tmp_path, config_hash=h)
    generate_tool_artifacts(ctx, ["cursor"])
    mdc = tmp_path / ".cursor" / "rules" / "veritydocs-core.mdc"
    meta = parse_embedded_meta(mdc)
    assert meta is not None
    assert meta[1] == h
    mcp = tmp_path / ".cursor" / "mcp.json"
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert data[ARTIFACT_META_KEY]["configHash"] == h
