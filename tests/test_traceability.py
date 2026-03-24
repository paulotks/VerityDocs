from pathlib import Path

from veritydocs.traceability.engine import build_traceability
from veritydocs.traceability.parser import (
    parse_dec_ids,
    parse_flow_ids,
    parse_rastreio,
    parse_rastreio_decs,
    parse_rastreio_flows,
    parse_req_ids,
    parse_spec_links,
)
from veritydocs.traceability.reporter import render_json, render_markdown


def test_parse_functions_extract_ids(tmp_path: Path):
    prd = tmp_path / "PRD.md"
    prd.write_text(
        "### `REQ-CTX-001` contexto\n-> SPEC: [Arquitetura](../SPEC/00-visao-arquitetura.md)\n",
        encoding="utf-8",
    )
    spec = tmp_path / "SPEC.md"
    spec.write_text("Rastreio PRD: REQ-CTX-001", encoding="utf-8")

    reqs = parse_req_ids([prd])
    traces = parse_rastreio([spec])
    links = parse_spec_links([prd])

    assert reqs[0].req_id == "REQ-CTX-001"
    assert traces[0].req_id == "REQ-CTX-001"
    assert links[0].target.endswith("00-visao-arquitetura.md")


def test_traceability_matrix(sample_project: Path):
    report = build_traceability(sample_project / "docs")
    assert len(report.matrix) >= 1
    assert report.phantom_ids == []
    assert report.orphan_reqs == []
    df = report.dec_flow
    assert df.dec_orphan_in_spec == []
    assert df.flow_orphan_in_spec == []


def test_dec_flow_crossref_parser(tmp_path: Path):
    docs = tmp_path / "docs"
    (docs / "audit").mkdir(parents=True)
    (docs / "flows").mkdir(parents=True)
    (docs / "SPEC").mkdir(parents=True)
    (docs / "audit" / "decisions-log.md").write_text(
        "# Log\n\n## DEC-001\nEscolha X.\n",
        encoding="utf-8",
    )
    (docs / "flows" / "checkout.md").write_text(
        "# Flow\n\nFLOW-CHECKOUT diagram.\n",
        encoding="utf-8",
    )
    spec_ok = docs / "SPEC" / "mod.md"
    spec_ok.write_text(
        "Rastreio PRD: REQ-CTX-001 DEC-001 FLOW-CHECKOUT\nMais texto com DEC-001.\n",
        encoding="utf-8",
    )
    report = build_traceability(docs)
    df = report.dec_flow
    assert "DEC-001" in df.dec_ids_in_log
    assert "DEC-001" in df.dec_ids_in_spec
    assert df.dec_orphan_in_spec == []
    assert df.dec_not_in_spec == []
    assert "FLOW-CHECKOUT" in df.flow_ids_in_flows
    assert "FLOW-CHECKOUT" in df.flow_ids_in_spec
    assert df.flow_orphan_in_spec == []
    assert df.flow_not_in_spec == []

    spec_bad = docs / "SPEC" / "orphan.md"
    spec_bad.write_text("Ver DEC-999 e FLOW-MISSING.\n", encoding="utf-8")
    report2 = build_traceability(docs)
    assert "DEC-999" in report2.dec_flow.dec_orphan_in_spec
    assert "FLOW-MISSING" in report2.dec_flow.flow_orphan_in_spec


def test_parse_rastreio_decs_flows_on_trace_line(tmp_path: Path):
    spec = tmp_path / "s.md"
    spec.write_text(
        "Rastreio PRD: REQ-CTX-001 DEC-002 FLOW-ZZ\n",
        encoding="utf-8",
    )
    assert [x.dec_id for x in parse_rastreio_decs([spec])] == ["DEC-002"]
    assert [x.flow_id for x in parse_rastreio_flows([spec])] == ["FLOW-ZZ"]
    assert [d.dec_id for d in parse_dec_ids([spec])] == ["DEC-002"]
    assert [f.flow_id for f in parse_flow_ids([spec])] == ["FLOW-ZZ"]


def test_report_renderers(sample_project: Path):
    report = build_traceability(sample_project / "docs")
    md = render_markdown(report)
    js = render_json(report)
    assert "# Matriz de Rastreabilidade" in md
    assert "DEC-* e FLOW-*" in md
    assert '"matrix"' in js
    assert '"dec_flow"' in js
