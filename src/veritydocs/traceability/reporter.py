from __future__ import annotations

import json
from pathlib import Path

from veritydocs.traceability.engine import TraceabilityReportData


def render_markdown(report: TraceabilityReportData) -> str:
    df = report.dec_flow
    lines = [
        "# Matriz de Rastreabilidade",
        "",
        "| REQ / grupo | PRD | SPEC | Notas |",
        "|-------------|-----|------|-------|",
    ]
    for row in report.matrix:
        lines.append(f"| `{row['req_id']}` | {row['prd']} | {row['spec']} | {row['notes']} |")
    dec_flow_rows: list[tuple[str, list[str]]] = [
        ("DEC na SPEC sem registo em `audit/decisions-log.md`", df.dec_orphan_in_spec),
        ("DEC no registo sem menção na SPEC", df.dec_not_in_spec),
        ("DEC só em linha Rastreio sem registo no log", df.dec_orphan_on_trace_line),
        ("FLOW na SPEC sem definição em `docs/flows/`", df.flow_orphan_in_spec),
        ("FLOW em `docs/flows/` sem menção na SPEC", df.flow_not_in_spec),
        ("FLOW só em linha Rastreio sem ficheiro em flows/", df.flow_orphan_on_trace_line),
    ]
    lines += [
        "",
        "## DEC-* e FLOW-* (SPEC vs audit e flows)",
        "",
        "| Indicador | Quantidade | IDs |",
        "|-----------|------------|-----|",
    ]
    for label, ids in dec_flow_rows:
        detail = ", ".join(ids)
        lines.append(f"| {label} | {len(ids)} | {detail} |")
    lines += [
        "",
        "## Resultados (REQ)",
        "",
        f"- IDs orfaos na SPEC: {len(report.orphan_reqs)}",
        f"- IDs sem cobertura na SPEC: {len(report.phantom_ids)}",
    ]
    return "\n".join(lines) + "\n"


def render_json(report: TraceabilityReportData) -> str:
    df = report.dec_flow
    return json.dumps(
        {
            "matrix": report.matrix,
            "orphan_reqs": report.orphan_reqs,
            "phantom_ids": report.phantom_ids,
            "dec_flow": {
                "dec_ids_in_log": df.dec_ids_in_log,
                "dec_ids_in_spec": df.dec_ids_in_spec,
                "dec_orphan_in_spec": df.dec_orphan_in_spec,
                "dec_not_in_spec": df.dec_not_in_spec,
                "dec_orphan_on_trace_line": df.dec_orphan_on_trace_line,
                "flow_ids_in_flows": df.flow_ids_in_flows,
                "flow_ids_in_spec": df.flow_ids_in_spec,
                "flow_orphan_in_spec": df.flow_orphan_in_spec,
                "flow_not_in_spec": df.flow_not_in_spec,
                "flow_orphan_on_trace_line": df.flow_orphan_on_trace_line,
            },
        },
        indent=2,
        ensure_ascii=False,
    )


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
