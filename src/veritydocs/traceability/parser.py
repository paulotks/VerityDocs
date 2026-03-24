from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REQ_RE = re.compile(r"REQ-[A-Z]+(?:-[A-Z0-9]+)*-\d+")
FUNC_REQ_RE = re.compile(r"REQ-FUNC-\d+")
DEC_RE = re.compile(r"\bDEC-\d+\b")
FLOW_RE = re.compile(r"\bFLOW-[A-Za-z0-9][A-Za-z0-9_-]*\b")
TRACE_RE = re.compile(r"(?:Rastreio PRD|PRD trace)\s*:\s*(.+)", re.IGNORECASE)
SPEC_LINK_RE = re.compile(r"->\s*SPEC:\s*\[([^\]]+)\]\(([^)]+)\)")


@dataclass
class ReqDef:
    req_id: str
    file: str


@dataclass
class SpecTrace:
    req_id: str
    file: str


@dataclass
class SpecLink:
    req_id: str
    source_file: str
    target: str


@dataclass
class DecDef:
    dec_id: str
    file: str


@dataclass
class FlowDef:
    flow_id: str
    file: str


def _normalize_flow_id(raw: str) -> str:
    return raw.upper()


def parse_dec_ids(markdown_files: list[Path]) -> list[DecDef]:
    """Extract DEC-* identifiers from markdown (e.g. decisions-log or SPEC)."""
    defs: list[DecDef] = []
    for file in markdown_files:
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            continue
        for dec_id in sorted(set(DEC_RE.findall(text))):
            defs.append(DecDef(dec_id=dec_id, file=file.as_posix()))
    return defs


def parse_flow_ids(markdown_files: list[Path]) -> list[FlowDef]:
    """Extract FLOW-* identifiers from markdown (flows/ or SPEC cross-refs)."""
    defs: list[FlowDef] = []
    for file in markdown_files:
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            continue
        for raw in sorted(set(FLOW_RE.findall(text))):
            defs.append(FlowDef(flow_id=_normalize_flow_id(raw), file=file.as_posix()))
    return defs


def parse_rastreio_line_ids(line: str) -> tuple[list[str], list[str], list[str]]:
    """Parse REQ, DEC, and FLOW ids from a 'Rastreio PRD' / trace line tail."""
    tail = ""
    m = TRACE_RE.search(line)
    if m:
        tail = m.group(1)
    combined = tail if tail else line
    reqs = sorted(set(REQ_RE.findall(combined)))
    decs = sorted(set(DEC_RE.findall(combined)))
    flows = sorted({_normalize_flow_id(x) for x in FLOW_RE.findall(combined)})
    return reqs, decs, flows


def parse_req_ids(prd_files: list[Path]) -> list[ReqDef]:
    defs: list[ReqDef] = []
    for file in prd_files:
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            continue
        for req_id in sorted(set(REQ_RE.findall(text))):
            defs.append(ReqDef(req_id=req_id, file=file.as_posix()))
    return defs


def parse_rastreio(spec_files: list[Path]) -> list[SpecTrace]:
    traces: list[SpecTrace] = []
    for file in spec_files:
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            if not TRACE_RE.search(line):
                continue
            reqs, _, _ = parse_rastreio_line_ids(line)
            for req_id in reqs:
                traces.append(SpecTrace(req_id=req_id, file=file.as_posix()))
    return traces


def parse_rastreio_decs(spec_files: list[Path]) -> list[DecDef]:
    """DEC-* apenas em linhas `Rastreio PRD` / `PRD trace` (espelha o rastreio de REQ)."""
    defs: list[DecDef] = []
    for file in spec_files:
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            if not TRACE_RE.search(line):
                continue
            _, decs, _ = parse_rastreio_line_ids(line)
            for dec_id in decs:
                defs.append(DecDef(dec_id=dec_id, file=file.as_posix()))
    return defs


def parse_rastreio_flows(spec_files: list[Path]) -> list[FlowDef]:
    """FLOW-* apenas em linhas `Rastreio PRD` / `PRD trace`."""
    defs: list[FlowDef] = []
    for file in spec_files:
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            if not TRACE_RE.search(line):
                continue
            _, _, flows = parse_rastreio_line_ids(line)
            for flow_id in flows:
                defs.append(FlowDef(flow_id=flow_id, file=file.as_posix()))
    return defs


def parse_dec_ids_from_files(files: list[Path]) -> list[str]:
    """Identificadores DEC-* únicos (texto completo dos ficheiros)."""
    return sorted({d.dec_id for d in parse_dec_ids(files)})


def parse_flow_ids_from_files(files: list[Path]) -> list[str]:
    """Identificadores FLOW-* únicos (normalizados em maiúsculas)."""
    return sorted({f.flow_id for f in parse_flow_ids(files)})


def parse_spec_links(prd_files: list[Path]) -> list[SpecLink]:
    out: list[SpecLink] = []
    for file in prd_files:
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            continue
        last_req_id = ""
        for line in text.splitlines():
            req_ids = REQ_RE.findall(line)
            if req_ids:
                last_req_id = req_ids[-1]
            m = SPEC_LINK_RE.search(line)
            if m and last_req_id:
                out.append(
                    SpecLink(req_id=last_req_id, source_file=file.as_posix(), target=m.group(2))
                )
    return out
