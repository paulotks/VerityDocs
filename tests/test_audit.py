import csv
import json
from io import StringIO
from pathlib import Path

from veritydocs.audit.auditor import audit_module
from veritydocs.audit.consolidator import consolidate_global
from veritydocs.audit.global_steps import (
    audit_cross_module,
    audit_decision_coverage,
    audit_flow_coverage,
)
from veritydocs.audit.module_map import load_module_mapping
from veritydocs.audit.reporters import render_module_audit_markdown, render_traceability_csv
from veritydocs.config import ModuleMapping


def test_audit_module(sample_project: Path):
    modules = load_module_mapping(sample_project / "docs" / "audit" / "step0-module-mapping.json")
    result = audit_module(sample_project, modules[0])
    assert result.module_id == "M01"
    assert result.executive_summary.total_findings == 0
    assert result.cross_check.coverage_rows


def test_audit_reporters_csv_and_markdown(sample_project: Path) -> None:
    modules = load_module_mapping(sample_project / "docs" / "audit" / "step0-module-mapping.json")
    result = audit_module(sample_project, modules[0])
    csv_text = render_traceability_csv(result.cross_check.coverage_rows)
    rows = list(csv.reader(StringIO(csv_text)))
    assert rows[0] == ["PRD-ID", "SPEC-Path", "Status", "Severidade", "Comentario"]
    assert len(rows) == 1 + len(result.cross_check.coverage_rows)
    md = render_module_audit_markdown(result)
    assert f"# Auditoria — {result.module_id}" in md
    assert "## Resumo executivo" in md
    assert "## Findings PRD" in md
    assert "## Findings SPEC" in md


def test_audit_cross_module_detects_untraced_foreign_req(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "PRD").mkdir(parents=True)
    (docs / "SPEC").mkdir(parents=True)
    (docs / "PRD" / "m1.md").write_text("### REQ-CTX-001\n", encoding="utf-8")
    (docs / "PRD" / "m2.md").write_text("### REQ-OBJ-001\n", encoding="utf-8")
    (docs / "SPEC" / "s1.md").write_text("Rastreio PRD: REQ-CTX-001\n", encoding="utf-8")
    (docs / "SPEC" / "s2.md").write_text(
        "Ver impacto REQ-CTX-001 noutro modulo.\nRastreio PRD: REQ-OBJ-001\n",
        encoding="utf-8",
    )
    modules = [
        ModuleMapping(
            module_id="M01",
            title="a",
            prd_path="docs/PRD/m1.md",
            spec_primary=["docs/SPEC/s1.md"],
            spec_secondary=[],
        ),
        ModuleMapping(
            module_id="M02",
            title="b",
            prd_path="docs/PRD/m2.md",
            spec_primary=["docs/SPEC/s2.md"],
            spec_secondary=[],
        ),
    ]
    findings = audit_cross_module(tmp_path, modules)
    assert len(findings) == 1
    assert findings[0].type == "cross_module_sem_rastreio"
    assert "REQ-CTX-001" in findings[0].req_ids


def test_audit_decision_coverage_missing_dec_in_spec(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "audit").mkdir(parents=True)
    (docs / "SPEC").mkdir(parents=True)
    (docs / "audit" / "decisions-log.md").write_text(
        "## Log\n\nDEC-001 descricao.\n",
        encoding="utf-8",
    )
    (docs / "SPEC" / "x.md").write_text("Sem decisoes aqui.\n", encoding="utf-8")
    modules = [
        ModuleMapping(
            module_id="M01",
            title="x",
            prd_path="docs/PRD/x.md",
            spec_primary=["docs/SPEC/x.md"],
            spec_secondary=[],
        ),
    ]
    findings = audit_decision_coverage(docs, modules)
    assert len(findings) == 1
    assert findings[0].req_ids == ["DEC-001"]


def test_audit_flow_coverage_missing_func_req(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "PRD").mkdir(parents=True)
    (docs / "flows").mkdir(parents=True)
    (docs / "PRD" / "f.md").write_text("### REQ-FUNC-007\n", encoding="utf-8")
    (docs / "flows" / "_index.md").write_text("# Fluxos\n", encoding="utf-8")
    findings = audit_flow_coverage(docs)
    assert len(findings) == 1
    assert "REQ-FUNC-007" in findings[0].req_ids


def test_consolidate_global_merges_pipeline_steps(tmp_path: Path) -> None:
    mod_json = tmp_path / "m.json"
    mod_json.write_text(
        json.dumps(
            {
                "module_id": "M01",
                "executive_summary": {"total_findings": 2},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "global.json"
    cross_finding = {
        "id": "XMOD-001",
        "severity": "importante",
        "type": "x",
        "req_ids": [],
        "descricao": "",
    }
    consolidate_global(
        [mod_json],
        out,
        cross_module_findings=[cross_finding],
        decision_findings=[],
        flow_findings=[],
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["aggregate_executive_summary"]["per_module_findings"] == 2
    assert data["aggregate_executive_summary"]["global_pipeline_findings"] == 1
    assert data["aggregate_executive_summary"]["total_findings"] == 3
    assert data["pipeline_steps"]["step2_cross_module"]["count"] == 1
