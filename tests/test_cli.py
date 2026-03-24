import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from veritydocs.cli import app
from veritydocs.scaffold.generator import init_project

runner = CliRunner()


def test_cli_trace_json(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    result = runner.invoke(
        app,
        ["trace", "--config", str(tmp_path / "veritydocs.config.yaml"), "--format", "json"],
    )
    assert result.exit_code == 0
    assert '"matrix"' in result.stdout


def test_cli_check_missing_config_returns_usage_error(tmp_path: Path):
    result = runner.invoke(app, ["check", "--config", str(tmp_path / "missing.json")])
    assert result.exit_code == 2
    assert "Ficheiro de config nao encontrado" in result.stdout


def test_cli_check_invalid_json_returns_usage_error(tmp_path: Path):
    cfg = tmp_path / "VerityDocs.config.json"
    cfg.write_text("{invalid", encoding="utf-8")
    result = runner.invoke(app, ["check", "--config", str(cfg)])
    assert result.exit_code == 2
    assert "JSON invalido" in result.stdout


def test_cli_check_empty_config_yaml_returns_usage_error(tmp_path: Path):
    cfg = tmp_path / "veritydocs.config.yaml"
    cfg.write_text("", encoding="utf-8")
    result = runner.invoke(app, ["check", "--config", str(cfg)])
    assert result.exit_code == 2
    assert "Config invalida" in result.stdout
    assert "vazio" in result.stdout


def test_cli_check_config_root_not_object_returns_usage_error(tmp_path: Path):
    cfg = tmp_path / "veritydocs.config.yaml"
    cfg.write_text(yaml.safe_dump(["not", "a", "map"], allow_unicode=True), encoding="utf-8")
    result = runner.invoke(app, ["check", "--config", str(cfg)])
    assert result.exit_code == 2
    assert "Config invalida" in result.stdout
    assert "objeto" in result.stdout


def test_cli_audit_all_generates_output(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    result = runner.invoke(
        app,
        ["audit", "--all", "--config", str(tmp_path / "veritydocs.config.yaml")],
    )
    assert result.exit_code == 0
    out_m01 = tmp_path / "docs" / "audit" / "output" / "M01"
    assert (out_m01 / "consolidated.json").exists()
    csv_path = out_m01 / "traceability.csv"
    assert csv_path.exists()
    csv_lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(csv_lines) >= 2
    summary = (out_m01 / "audit-summary.md").read_text(encoding="utf-8")
    assert "# Auditoria — M01" in summary
    assert "## Resumo executivo" in summary


def test_cli_intake_batch(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    payload = {
        "description": "Sistema deve enviar email na confirmacao",
        "ator": "operador",
        "regra": "enviar email",
        "criterio_aceite": "email recebido",
        "escopo": "MVP",
        "confirmed": True,
    }
    result = runner.invoke(
        app,
        ["intake", "--batch", "--config", str(tmp_path / "veritydocs.config.yaml")],
        input=json.dumps(payload),
    )
    assert result.exit_code == 0
    assert (tmp_path / "docs" / "changes" / "intake-draft.json").exists()


def test_cli_report_html(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    output = tmp_path / "docs" / "report.html"
    result = runner.invoke(
        app,
        ["report", "--config", str(tmp_path / "veritydocs.config.yaml"), "--output", str(output)],
    )
    assert result.exit_code == 0
    assert output.exists()


def test_cli_status_json(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    cfg = str(tmp_path / "veritydocs.config.yaml")
    result = runner.invoke(app, ["status", "--config", cfg, "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["project"]["name"] == "Demo"
    assert "check" in data
    assert "traceability" in data
    assert data["mcp"]["context7"]["enabled"] is True
    assert "resolve_tool" in data["mcp"]["context7"]


def test_cli_status_md(tmp_path: Path):
    init_project(tmp_path, "Demo", "en", "software", ["cursor"])
    cfg = str(tmp_path / "veritydocs.config.yaml")
    result = runner.invoke(app, ["status", "--config", cfg, "--format", "md"])
    assert result.exit_code == 0
    assert "# VerityDocs status" in result.stdout


def test_cli_status_invalid_format(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    cfg = str(tmp_path / "veritydocs.config.yaml")
    result = runner.invoke(app, ["status", "--config", cfg, "--format", "text"])
    assert result.exit_code == 2


def test_cli_status_change_not_found(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    cfg = str(tmp_path / "veritydocs.config.yaml")
    result = runner.invoke(
        app,
        ["status", "--config", cfg, "--change", "missing-change", "--format", "json"],
    )
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["focused_change"]["error"] == "not_found"


def test_cli_instructions_propose_json(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    cfg = str(tmp_path / "veritydocs.config.yaml")
    result = runner.invoke(
        app,
        ["instructions", "propose", "--config", cfg, "--format", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["workflow"] == "propose"
    assert "body_markdown" in data
    assert "vrtdocs:propose" in data["body_markdown"]


def test_cli_instructions_unknown_workflow(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    cfg = str(tmp_path / "veritydocs.config.yaml")
    result = runner.invoke(
        app,
        ["instructions", "nope", "--config", cfg],
    )
    assert result.exit_code == 2


def test_cli_flows_generate_json(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    cfg = str(tmp_path / "veritydocs.config.yaml")
    result = runner.invoke(
        app,
        ["flows", "generate", "--config", cfg, "--format", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["functional_count"] >= 1
    assert len(data["written"]) == 2
    assert (tmp_path / "docs" / "flows" / "FLOW-prd-functional.md").is_file()


def test_cli_sync_regenerates(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    cfg = str(tmp_path / "veritydocs.config.yaml")
    rules = tmp_path / ".cursor" / "rules" / "veritydocs-core.mdc"
    assert rules.is_file()
    rules.write_text("# stale\n", encoding="utf-8")
    result = runner.invoke(app, ["sync", "--config", cfg])
    assert result.exit_code == 0
    text = rules.read_text(encoding="utf-8")
    assert not text.lstrip().startswith("# stale")


def test_cli_workflows_validate_ok(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    cfg = str(tmp_path / "veritydocs.config.yaml")
    result = runner.invoke(app, ["workflows", "validate", "--config", cfg])
    assert result.exit_code == 0
    assert "workflows.yaml" in result.stdout


def test_cli_init_rejects_unknown_tools(tmp_path: Path):
    result = runner.invoke(
        app,
        ["init", "--dir", str(tmp_path), "--tools", "gemini", "--name", "X"],
    )
    assert result.exit_code == 2
    assert "sem adaptador" in result.stdout
    assert "gemini" in result.stdout


def test_cli_init_accepts_registered_tools(tmp_path: Path):
    result = runner.invoke(
        app,
        ["init", "--dir", str(tmp_path), "--tools", "cursor,claude", "--name", "X"],
    )
    assert result.exit_code == 0
    assert (tmp_path / ".cursor" / "rules" / "veritydocs-core.mdc").is_file()
    assert (tmp_path / "CLAUDE.md").is_file()


def test_cli_init_tools_dedupes_ids(tmp_path: Path):
    result = runner.invoke(
        app,
        ["init", "--dir", str(tmp_path), "--tools", "cursor,cursor", "--name", "X"],
    )
    assert result.exit_code == 0
    cfg_path = tmp_path / "veritydocs.config.yaml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert data["tools"] == ["cursor"]


def test_cli_sync_no_tools_exits_zero(tmp_path: Path):
    (tmp_path / "veritydocs.config.yaml").write_text(
        """
version: "1.0"
project:
  name: X
  language: pt-BR
  domain: software
docs_root: docs
tools: []
profile: core
""".strip(),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["sync", "--config", str(tmp_path / "veritydocs.config.yaml")])
    assert result.exit_code == 0
