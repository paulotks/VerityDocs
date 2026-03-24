"""Unit tests for cli_status helpers (status / instructions payloads)."""

from __future__ import annotations

from pathlib import Path

import pytest

from veritydocs.cli_status import (
    build_instructions_payload,
    build_status_payload,
    parse_output_format,
    render_instructions_markdown,
    render_status_markdown,
)
from veritydocs.config import load_config
from veritydocs.scaffold.generator import init_project


def test_parse_output_format() -> None:
    assert parse_output_format("json") == "json"
    assert parse_output_format("MD") == "md"
    assert parse_output_format("markdown") == "md"
    with pytest.raises(ValueError, match="invalido"):
        parse_output_format("text")


def test_build_status_payload_structure(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "en", "software", ["cursor"])
    cfg_path = tmp_path / "veritydocs.config.yaml"
    cfg = load_config(cfg_path)
    payload = build_status_payload(cfg, cfg_path)
    assert payload["project"]["name"] == "Demo"
    assert "check" in payload and "rows" in payload["check"]
    assert "traceability" in payload
    assert payload["changes"]["open"] == []


def test_build_status_payload_focused_change(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    cfg_path = tmp_path / "veritydocs.config.yaml"
    cfg = load_config(cfg_path)
    ch = tmp_path / "docs" / "changes" / "my-change"
    ch.mkdir(parents=True)
    (ch / "metadata.yaml").write_text(
        "version: '1'\n"
        "change_type: flow\n"
        "status: draft\n"
        "created_at: '2025-01-01T00:00:00+00:00'\n"
        "updated_at: '2025-01-01T00:00:00+00:00'\n",
        encoding="utf-8",
    )
    payload = build_status_payload(cfg, cfg_path, change="my-change")
    fc = payload.get("focused_change")
    assert isinstance(fc, dict)
    assert fc.get("name") == "my-change"
    assert fc.get("metadata", {}).get("status") == "draft"


def test_build_status_payload_focused_not_found(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "en", "software", ["cursor"])
    cfg_path = tmp_path / "veritydocs.config.yaml"
    cfg = load_config(cfg_path)
    payload = build_status_payload(cfg, cfg_path, change="missing")
    assert payload["focused_change"]["error"] == "not_found"


def test_build_instructions_payload(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "en", "software", ["cursor"])
    cfg_path = tmp_path / "veritydocs.config.yaml"
    cfg = load_config(cfg_path)
    p = build_instructions_payload("apply", cfg, cfg_path, change="c1")
    assert p["workflow"] == "apply"
    assert p["change"] == "c1"
    assert "veritydocs check" in " ".join(p["recommended_cli"])
    assert "body_markdown" in p and len(p["body_markdown"]) > 50


def test_build_instructions_unknown_workflow(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "en", "software", ["cursor"])
    cfg_path = tmp_path / "veritydocs.config.yaml"
    cfg = load_config(cfg_path)
    with pytest.raises(ValueError, match="desconhecido"):
        build_instructions_payload("nope", cfg, cfg_path)


def test_render_status_markdown_en(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "en", "software", ["cursor"])
    cfg_path = tmp_path / "veritydocs.config.yaml"
    cfg = load_config(cfg_path)
    payload = build_status_payload(cfg, cfg_path)
    md = render_status_markdown(payload, "en")
    assert "# VerityDocs status" in md
    assert "Demo" in md


def test_render_instructions_markdown_roundtrip(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "en", "software", ["cursor"])
    cfg_path = tmp_path / "veritydocs.config.yaml"
    cfg = load_config(cfg_path)
    payload = build_instructions_payload("sync", cfg, cfg_path)
    md = render_instructions_markdown(payload)
    assert "vrtdocs:sync" in md
    assert "Recommended CLI" in md


def test_build_status_payload_decisions_from_log(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "en", "software", ["cursor"])
    log = tmp_path / "docs" / "audit" / "decisions-log.md"
    log.write_text("Registered DEC-1 and DEC-2.\n", encoding="utf-8")
    cfg_path = tmp_path / "veritydocs.config.yaml"
    cfg = load_config(cfg_path)
    payload = build_status_payload(cfg, cfg_path)
    assert payload["decisions"]["dec_ids_count"] >= 2
