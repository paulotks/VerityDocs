import json
from pathlib import Path

from veritydocs.check.consistency import run_checks
from veritydocs.config import load_config, save_config_yaml
from veritydocs.scaffold.generator import init_project


def test_check_runs(sample_project: Path):
    rows = run_checks(sample_project / "docs", strict=False)
    assert any(r[0] == "REQ unico" for r in rows)


def test_check_strict_flags_placeholders(tmp_path: Path):
    docs = tmp_path / "docs"
    (docs / "PRD").mkdir(parents=True)
    (docs / "SPEC").mkdir(parents=True)
    (docs / "audit").mkdir(parents=True)
    (docs / "PRD" / "_index.md").write_text("# idx", encoding="utf-8")
    (docs / "SPEC" / "_index.md").write_text("# idx", encoding="utf-8")
    (docs / "audit" / "step0-module-mapping.json").write_text(
        json.dumps({"modules": []}),
        encoding="utf-8",
    )
    (docs / "PRD" / "x.md").write_text("REQ-CTX-001\nTODO", encoding="utf-8")
    (docs / "SPEC" / "y.md").write_text("Rastreio PRD: REQ-CTX-001", encoding="utf-8")

    rows = run_checks(docs, strict=True)
    placeholders = next(r for r in rows if r[0] == "Placeholders pendentes")
    assert placeholders[1] == "ERROR"


def test_check_loads_plugin(tmp_path: Path, monkeypatch):
    plugin_mod = tmp_path / "my_plugin.py"
    plugin_mod.write_text(
        "def my_rule(docs_root):\n    return [('Plugin custom', 'OK', docs_root.as_posix())]\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(tmp_path.as_posix())
    rows = run_checks(tmp_path, plugins=["my_plugin:my_rule"])
    assert any(row[0] == "Plugin custom" for row in rows)


def test_check_toolgen_drift_ok_after_cursor_sync(tmp_path: Path) -> None:
    init_project(tmp_path, "P", "pt-BR", "software", ["cursor"])
    cfg_path = tmp_path / "veritydocs.config.yaml"
    rows = run_checks(tmp_path / "docs", config_path=cfg_path)
    drift = next(r for r in rows if r[0] == "Artefactos toolgen — drift de config")
    assert drift[1] == "OK"


def test_check_toolgen_drift_warn_when_config_changes(tmp_path: Path) -> None:
    init_project(tmp_path, "P", "pt-BR", "software", ["cursor"])
    cfg_path = tmp_path / "veritydocs.config.yaml"
    cfg = load_config(cfg_path)
    cfg.project = cfg.project.model_copy(update={"name": "Renamed"})
    save_config_yaml(cfg_path, cfg)
    rows = run_checks(tmp_path / "docs", config_path=cfg_path)
    drift = next(r for r in rows if r[0] == "Artefactos toolgen — drift de config")
    assert drift[1] == "WARN"
    assert "veritydocs sync" in drift[2]


def test_check_toolgen_drift_warn_when_metadata_stripped(tmp_path: Path) -> None:
    init_project(tmp_path, "P", "pt-BR", "software", ["cursor"])
    cfg_path = tmp_path / "veritydocs.config.yaml"
    rule_file = tmp_path / ".cursor" / "rules" / "veritydocs-core.mdc"
    text = rule_file.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("<!-- VerityDocs")]
    rule_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rows = run_checks(tmp_path / "docs", config_path=cfg_path)
    drift = next(r for r in rows if r[0] == "Artefactos toolgen — drift de config")
    assert drift[1] == "WARN"
    assert "Sem metadados" in drift[2]


def test_check_toolgen_skips_drift_without_config_path(sample_project: Path) -> None:
    rows = run_checks(sample_project / "docs", strict=False)
    assert not any(r[0] == "Artefactos toolgen — drift de config" for r in rows)


def test_check_toolgen_warn_when_tools_configured_but_no_artifacts(tmp_path: Path) -> None:
    init_project(tmp_path, "P", "pt-BR", "software", [])
    cfg_path = tmp_path / "veritydocs.config.yaml"
    cfg = load_config(cfg_path)
    save_config_yaml(cfg_path, cfg.model_copy(update={"tools": ["cursor"]}))
    rows = run_checks(tmp_path / "docs", config_path=cfg_path)
    drift = next(r for r in rows if r[0] == "Artefactos toolgen — drift de config")
    assert drift[1] == "WARN"
    assert "nenhum artefato" in drift[2].lower()
