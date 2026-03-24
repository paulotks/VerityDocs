import json
from pathlib import Path

import pytest
import yaml

from veritydocs.config import CONFIG_FILENAMES, load_config, resolve_config_path, save_config_yaml


def test_load_json_config(tmp_path: Path):
    p = tmp_path / "VerityDocs.config.json"
    p.write_text(
        json.dumps(
            {
                "project": {"name": "X", "language": "en", "domain": "software"},
                "docs_root": "docs",
            }
        ),
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.project.name == "X"
    assert cfg.tools == []
    assert cfg.profile == "core"
    assert cfg.mcp.context7.enabled is True


def test_load_json_ignores_unknown_top_level_keys(tmp_path: Path):
    p = tmp_path / "VerityDocs.config.json"
    p.write_text(
        json.dumps(
            {
                "project": {"name": "Z", "language": "en", "domain": "software"},
                "docs_root": "docs",
                "future_field": {"x": 1},
            }
        ),
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.project.name == "Z"


def test_resolve_prefers_yaml_over_json(tmp_path: Path):
    proj = {"name": "Yaml", "language": "en", "domain": "software"}
    (tmp_path / "veritydocs.config.yaml").write_text(
        yaml.safe_dump({"project": proj, "docs_root": "docs"}, allow_unicode=True),
        encoding="utf-8",
    )
    proj_json = {"name": "Json", "language": "en", "domain": "software"}
    (tmp_path / "VerityDocs.config.json").write_text(
        json.dumps({"project": proj_json, "docs_root": "docs"}),
        encoding="utf-8",
    )
    path = resolve_config_path(None, cwd=tmp_path)
    assert path.name == "veritydocs.config.yaml"
    assert load_config(path).project.name == "Yaml"


def test_load_yaml_with_bom(tmp_path: Path):
    p = tmp_path / "veritydocs.config.yaml"
    body = yaml.safe_dump(
        {"project": {"name": "Bom", "language": "en", "domain": "software"}, "docs_root": "docs"},
        allow_unicode=True,
    )
    p.write_text("\ufeff" + body, encoding="utf-8")
    assert load_config(p).project.name == "Bom"


def test_coerce_workflows_embedded_path(tmp_path: Path):
    p = tmp_path / "veritydocs.config.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "project": {"name": "W", "language": "en", "domain": "software"},
                "docs_root": "docs",
                "workflows": {"active": ["propose"], "path": "custom/workflows.yaml"},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.workflows.active == ["propose"]
    assert cfg.workflows_file.path == "custom/workflows.yaml"


def test_config_filenames_order():
    assert CONFIG_FILENAMES[0] == "veritydocs.config.yaml"
    assert "VerityDocs.config.json" in CONFIG_FILENAMES


def test_empty_yaml_raises(tmp_path: Path):
    p = tmp_path / "veritydocs.config.yaml"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="vazio"):
        load_config(p)


def test_load_yaml_roundtrip(tmp_path: Path):
    p = tmp_path / "veritydocs.config.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "project": {"name": "Y", "language": "pt-BR", "domain": "api"},
                "docs_root": "docs",
                "tools": ["cursor"],
                "profile": "core",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.tools == ["cursor"]
    save_config_yaml(tmp_path / "out.yaml", cfg)
    cfg2 = load_config(tmp_path / "out.yaml")
    assert cfg2.project.name == "Y"


def test_load_yaml_yml_suffix(tmp_path: Path):
    p = tmp_path / "veritydocs.config.yml"
    p.write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "project": {"name": "Z", "language": "en", "domain": "software"},
                "docs_root": "docs",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.project.name == "Z"


def test_resolve_config_path_explicit(tmp_path: Path):
    p = tmp_path / "custom.yaml"
    p.write_text("{}", encoding="utf-8")
    assert resolve_config_path(p).resolve() == p.resolve()


def test_load_config_rejects_non_object(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text("- list", encoding="utf-8")
    with pytest.raises(ValueError, match="objeto"):
        load_config(p)
