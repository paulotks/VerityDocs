from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from veritydocs.traceability.parser import (
    parse_dec_ids,
    parse_flow_ids,
    parse_rastreio,
    parse_rastreio_decs,
    parse_rastreio_flows,
    parse_req_ids,
    parse_spec_links,
)


@dataclass
class DecFlowCrossRef:
    """DEC-* e FLOW-* entre audit/decisions-log, docs/flows e ficheiros SPEC."""

    dec_ids_in_log: list[str]
    dec_ids_in_spec: list[str]
    dec_orphan_in_spec: list[str]
    dec_not_in_spec: list[str]
    dec_orphan_on_trace_line: list[str]
    flow_ids_in_flows: list[str]
    flow_ids_in_spec: list[str]
    flow_orphan_in_spec: list[str]
    flow_not_in_spec: list[str]
    flow_orphan_on_trace_line: list[str]


@dataclass
class TraceabilityReportData:
    matrix: list[dict[str, str]]
    orphan_reqs: list[str]
    phantom_ids: list[str]
    dec_flow: DecFlowCrossRef


def _build_dec_flow_crossref(docs_root: Path, spec_files: list[Path]) -> DecFlowCrossRef:
    log_path = docs_root / "audit" / "decisions-log.md"
    dec_files = [log_path] if log_path.is_file() else []
    dec_in_log = {d.dec_id for d in parse_dec_ids(dec_files)}
    dec_in_spec = {d.dec_id for d in parse_dec_ids(spec_files)}
    decs_on_trace = {d.dec_id for d in parse_rastreio_decs(spec_files)}

    flows_dir = docs_root / "flows"
    flow_files = sorted(flows_dir.glob("*.md")) if flows_dir.is_dir() else []
    flow_defined = {f.flow_id for f in parse_flow_ids(flow_files)}
    flow_in_spec = {f.flow_id for f in parse_flow_ids(spec_files)}
    flows_on_trace = {f.flow_id for f in parse_rastreio_flows(spec_files)}

    return DecFlowCrossRef(
        dec_ids_in_log=sorted(dec_in_log),
        dec_ids_in_spec=sorted(dec_in_spec),
        dec_orphan_in_spec=sorted(dec_in_spec - dec_in_log),
        dec_not_in_spec=sorted(dec_in_log - dec_in_spec),
        dec_orphan_on_trace_line=sorted(decs_on_trace - dec_in_log),
        flow_ids_in_flows=sorted(flow_defined),
        flow_ids_in_spec=sorted(flow_in_spec),
        flow_orphan_in_spec=sorted(flow_in_spec - flow_defined),
        flow_not_in_spec=sorted(flow_defined - flow_in_spec),
        flow_orphan_on_trace_line=sorted(flows_on_trace - flow_defined),
    )


def build_traceability(docs_root: Path) -> TraceabilityReportData:
    prd_dir = docs_root / "PRD"
    spec_dir = docs_root / "SPEC"
    prd_files = sorted(prd_dir.glob("*.md")) if prd_dir.exists() else []
    spec_files = sorted(spec_dir.glob("*.md")) if spec_dir.exists() else []

    req_defs = parse_req_ids(prd_files)
    traces = parse_rastreio(spec_files)
    links = parse_spec_links(prd_files)

    req_set = {r.req_id for r in req_defs}
    trace_set = {t.req_id for t in traces}
    link_set = {link.req_id for link in links}

    orphan = sorted(trace_set - req_set)
    phantom = sorted(req_set - (trace_set | link_set))

    by_req_prd: dict[str, set[str]] = defaultdict(set)
    by_req_spec: dict[str, set[str]] = defaultdict(set)
    for r in req_defs:
        by_req_prd[r.req_id].add(r.file)
    for t in traces:
        by_req_spec[t.req_id].add(t.file)
    for link in links:
        by_req_spec[link.req_id].add(link.target.split("#")[0])

    matrix = []
    for req in sorted(req_set):
        matrix.append(
            {
                "req_id": req,
                "prd": ", ".join(sorted(by_req_prd[req])),
                "spec": ", ".join(sorted(by_req_spec[req])),
                "notes": "Coberto" if by_req_spec[req] else "Nao coberto",
            }
        )
    dec_flow = _build_dec_flow_crossref(docs_root, spec_files)
    return TraceabilityReportData(
        matrix=matrix,
        orphan_reqs=orphan,
        phantom_ids=phantom,
        dec_flow=dec_flow,
    )
