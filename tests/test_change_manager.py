import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veritydocs.change_manager import (
    archive_change,
    create_change,
    mark_applied,
    read_metadata,
    validate_slug,
)
from veritydocs.cli import app
from veritydocs.scaffold.generator import init_project

runner = CliRunner()


def test_validate_slug_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        validate_slug("Bad_Slug")
    with pytest.raises(ValueError):
        validate_slug("archive")
    with pytest.raises(ValueError):
        validate_slug("a/b")


def test_create_mark_applied_archive_lifecycle(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    root = tmp_path
    r = create_change(
        root,
        "docs",
        "billing-v2",
        change_type="architecture",
        author="tester",
        summary="scope billing",
        language="pt-BR",
    )
    assert r.change_dir.is_dir()
    assert (r.change_dir / "proposal.md").is_file()
    assert (r.change_dir / "metadata.yaml").is_file()
    meta = read_metadata(r.change_dir)
    assert meta is not None
    assert meta.get("status") == "draft"

    mark_applied(root, "docs", "billing-v2")
    meta2 = read_metadata(r.change_dir)
    assert meta2 is not None
    assert meta2.get("status") == "applied"

    dest = archive_change(root, "docs", "billing-v2", language="pt-BR")
    assert "archive" in dest.parts
    assert not (root / "docs" / "changes" / "billing-v2").exists()
    meta3 = read_metadata(dest)
    assert meta3 is not None
    assert meta3.get("status") == "archived"
    assert meta3.get("original_slug") == "billing-v2"


def test_archive_requires_applied_without_force(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    create_change(tmp_path, "docs", "x-only", change_type="flow", language="en")
    with pytest.raises(ValueError, match="applied"):
        archive_change(tmp_path, "docs", "x-only", force=False)


def test_archive_force_from_draft(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "en", "software", ["cursor"])
    create_change(tmp_path, "docs", "draft-move", change_type="decision", language="en")
    dest = archive_change(tmp_path, "docs", "draft-move", force=True, language="en")
    assert dest.is_dir()
    m = read_metadata(dest)
    assert m is not None and m.get("status") == "archived"


def test_cli_change_create_and_archive(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    cfg = str(tmp_path / "veritydocs.config.yaml")
    r1 = runner.invoke(
        app,
        [
            "change",
            "create",
            "my-change",
            "--config",
            cfg,
            "--type",
            "requirement",
            "--summary",
            "test",
        ],
    )
    assert r1.exit_code == 0
    assert (tmp_path / "docs" / "changes" / "my-change" / "metadata.yaml").is_file()

    r2 = runner.invoke(app, ["change", "mark-applied", "my-change", "--config", cfg])
    assert r2.exit_code == 0

    r3 = runner.invoke(app, ["change", "archive", "my-change", "--config", cfg])
    assert r3.exit_code == 0
    readme = (tmp_path / "docs" / "changes" / "README.md").read_text(encoding="utf-8")
    assert "my-change" in readme

    payload = json.loads(
        runner.invoke(app, ["status", "--config", cfg, "--format", "json"]).stdout,
    )
    names = [c["name"] for c in payload["changes"]["open"]]
    assert "my-change" not in names
