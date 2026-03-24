from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from veritydocs.flows.diagrams import (
    build_functional_flowchart,
    build_journey_flowchart,
    wrap_markdown_doc,
)
from veritydocs.flows.extract import extract_functional_reqs, extract_journey_sections

GENERATED_TAG = "<!-- veritydocs:flows-generated -->"

FILE_FUNC = "FLOW-prd-functional.md"
FILE_JOURNEYS = "FLOW-prd-user-journeys.md"


@dataclass
class FlowGenResult:
    docs_root: str
    written: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    functional_count: int = 0
    journey_sections: int = 0


def _prd_files(prd_dir: Path) -> list[Path]:
    if not prd_dir.is_dir():
        return []
    return sorted(prd_dir.glob("*.md"))


def generate_prd_flows(
    docs_root: Path,
    *,
    dry_run: bool = False,
    lang: str = "pt-BR",
) -> FlowGenResult:
    """
    Gera ficheiros Markdown com Mermaid em `docs/flows/`, a partir de cabeçalhos
    `REQ-FUNC-*` e tabelas de jornada `REQ-JOR-*` no PRD.
    """
    prd_dir = docs_root / "PRD"
    flows_dir = docs_root / "flows"
    prd_files = _prd_files(prd_dir)
    result = FlowGenResult(docs_root=docs_root.as_posix())

    if not prd_files:
        result.warnings.append("no_prd_files")
        return result

    func_reqs = extract_functional_reqs(prd_files)
    result.functional_count = len(func_reqs)

    journeys = extract_journey_sections(prd_files)
    result.journey_sections = len(journeys)

    is_en = lang == "en"
    intro_func = (
        "Auto-derived from PRD headings `### `REQ-FUNC-*``. The arrow chain follows "
        "document order as a reading guide, not a technical dependency graph."
        if is_en
        else "Derivado automaticamente dos cabeçalhos `### `REQ-FUNC-*`` no PRD. A cadeia "
        "segue a ordem do documento como guia de leitura, não como grafo de dependências."
    )
    intro_j = (
        "Auto-derived from PRD user-journey tables under `### `REQ-JOR-*`` sections."
        if is_en
        else "Derivado automaticamente das tabelas de jornada em secções `### `REQ-JOR-*``."
    )

    func_body = build_functional_flowchart(func_reqs)
    func_md = wrap_markdown_doc(
        "FLOW-prd-functional",
        func_body,
        intro=intro_func,
        generated_tag=GENERATED_TAG,
    )

    journey_md_parts = [
        "# FLOW-prd-user-journeys",
        "",
        GENERATED_TAG,
        "",
        intro_j,
        "",
    ]
    for j in journeys:
        journey_md_parts.append(f"## `{j.req_id}`")
        journey_md_parts.append("")
        journey_md_parts.append(f"_Source: `{j.source_file}`_")
        journey_md_parts.append("")
        journey_md_parts.append("```mermaid")
        journey_md_parts.append(build_journey_flowchart(j))
        journey_md_parts.append("```")
        journey_md_parts.append("")

    journeys_md = "\n".join(journey_md_parts).rstrip() + "\n"

    if dry_run:
        return result

    flows_dir.mkdir(parents=True, exist_ok=True)
    p_func = flows_dir / FILE_FUNC
    p_j = flows_dir / FILE_JOURNEYS

    p_func.write_text(func_md, encoding="utf-8")
    result.written.append(p_func.as_posix())

    p_j.write_text(journeys_md, encoding="utf-8")
    result.written.append(p_j.as_posix())

    return result


def result_to_json(result: FlowGenResult) -> str:
    return json.dumps(
        {
            "docs_root": result.docs_root,
            "written": result.written,
            "warnings": result.warnings,
            "functional_count": result.functional_count,
            "journey_sections": result.journey_sections,
        },
        indent=2,
        ensure_ascii=False,
    ) + "\n"
