from pathlib import Path

from veritydocs.flows.diagrams import build_functional_flowchart, build_journey_flowchart
from veritydocs.flows.engine import FILE_FUNC, FILE_JOURNEYS, generate_prd_flows
from veritydocs.flows.extract import (
    JourneySection,
    ReqHeading,
    extract_functional_reqs,
    extract_journey_sections,
)
from veritydocs.scaffold.generator import init_project


def test_extract_functional_sorts_by_number(tmp_path: Path):
    prd = tmp_path / "03-requisitos-funcionais.md"
    prd.write_text(
        "### `REQ-FUNC-002` Segundo\n### `REQ-FUNC-001` Primeiro\n",
        encoding="utf-8",
    )
    got = extract_functional_reqs([prd])
    assert [h.req_id for h in got] == ["REQ-FUNC-001", "REQ-FUNC-002"]


def test_extract_journey_table(tmp_path: Path):
    prd = tmp_path / "02-jornada.md"
    prd.write_text(
        "### `REQ-JOR-001` Jornada\n\n"
        "| Step | Actor | System behaviour | Outcome |\n"
        "|------|-------|------------------|----------|\n"
        "| 1 | User | Login | OK |\n"
        "| 2 | User | Pay | Paid |\n",
        encoding="utf-8",
    )
    sections = extract_journey_sections([prd])
    assert len(sections) == 1
    assert sections[0].req_id == "REQ-JOR-001"
    assert len(sections[0].steps) == 2


def test_mermaid_functional_contains_chain():
    reqs = [
        ReqHeading("REQ-FUNC-001", "A", "p.md"),
        ReqHeading("REQ-FUNC-002", "B", "p.md"),
    ]
    m = build_functional_flowchart(reqs)
    assert "flowchart TD" in m
    assert "REQ-FUNC-001" in m
    assert "F0 --> F1" in m


def test_mermaid_journey_subgraph():
    sec = JourneySection(
        req_id="REQ-JOR-001",
        source_file="j.md",
        steps=[
            {"step": "1", "actor": "U", "system behaviour": "Go", "outcome": "x"},
            {"step": "2", "actor": "U", "system behaviour": "Done", "outcome": "y"},
        ],
    )
    m = build_journey_flowchart(sec)
    assert "subgraph" in m
    assert "REQ_JOR_001_S0 --> REQ_JOR_001_S1" in m


def test_generate_prd_flows_writes_files(sample_project: Path):
    docs = sample_project / "docs"
    assert (docs / "PRD").glob("*.md")
    r = generate_prd_flows(docs, dry_run=False, lang="pt-BR")
    assert (docs / "flows" / FILE_FUNC).is_file()
    assert (docs / "flows" / FILE_JOURNEYS).is_file()
    assert r.functional_count >= 1
    body = (docs / "flows" / FILE_FUNC).read_text(encoding="utf-8")
    assert "```mermaid" in body
    assert "REQ-FUNC-001" in body


def test_generate_dry_run_no_files(tmp_path: Path):
    init_project(tmp_path, "X", "en", "software", [])
    docs = tmp_path / "docs"
    r = generate_prd_flows(docs, dry_run=True, lang="en")
    assert r.written == []
    assert not (docs / "flows" / FILE_FUNC).exists()

