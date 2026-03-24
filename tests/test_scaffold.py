from pathlib import Path

import yaml

from veritydocs.scaffold.generator import init_project
from veritydocs.workflows_spec import load_workflows_yaml


def test_init_project_creates_config(tmp_path: Path):
    init_project(tmp_path, "Demo", "pt-BR", "software", ["cursor"])
    assert (tmp_path / "veritydocs.config.yaml").exists()
    assert (tmp_path / "docs" / "PRD" / "_index.md").exists()
    assert (tmp_path / "docs" / "PRD" / "00-visao-escopo.md").exists()
    wf = tmp_path / "veritydocs" / "workflows.yaml"
    assert wf.exists()
    spec = load_workflows_yaml(wf)
    assert spec.change_types["flow"].verify_rules
    cfg = yaml.safe_load((tmp_path / "veritydocs.config.yaml").read_text(encoding="utf-8"))
    assert cfg["tools"] == ["cursor"]


def test_init_project_uses_domain_template(tmp_path: Path):
    init_project(tmp_path, "API Demo", "pt-BR", "api", [])
    readme = (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")
    assert "Template orientado a APIs HTTP/REST." in readme
