from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from veritydocs.traceability.parser import REQ_RE

_HEADING_RE = re.compile(r"^###\s*`(REQ-[A-Z]+(?:-[A-Z0-9]+)*-\d+)`\s*(.*)$")


@dataclass(frozen=True)
class ReqHeading:
    req_id: str
    title: str
    source_file: str


@dataclass(frozen=True)
class JourneySection:
    req_id: str
    source_file: str
    steps: list[dict[str, str]]


def _sort_req_func_key(req_id: str) -> tuple[int, str]:
    m = re.search(r"-(\d+)$", req_id)
    n = int(m.group(1)) if m else 0
    return (n, req_id)


def extract_req_headings(prd_files: list[Path]) -> list[ReqHeading]:
    """Extrai cabeçalhos `### `REQ-...`` em ficheiros PRD."""
    out: list[ReqHeading] = []
    for path in prd_files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            m = _HEADING_RE.match(line.strip())
            if not m:
                continue
            req_id = m.group(1)
            if REQ_RE.fullmatch(req_id) is None:
                continue
            title = (m.group(2) or "").strip()
            title = title.strip("`").strip()
            out.append(ReqHeading(req_id=req_id, title=title, source_file=path.as_posix()))
    return out


def extract_functional_reqs(prd_files: list[Path]) -> list[ReqHeading]:
    """Requisitos funcionais: `REQ-FUNC-*` com cabeçalho `###`."""
    func = [h for h in extract_req_headings(prd_files) if h.req_id.startswith("REQ-FUNC-")]
    return sorted(func, key=lambda h: _sort_req_func_key(h.req_id))


def _split_table_row(line: str) -> list[str]:
    raw = line.strip()
    if not raw.startswith("|"):
        return []
    trimmed = raw.strip().strip("|")
    return [p.strip() for p in trimmed.split("|")]


def _parse_gfm_table(lines: list[str]) -> tuple[list[str] | None, list[list[str]]]:
    """Devolve cabeçalho e linhas de dados de uma tabela GFM (se válida)."""
    if len(lines) < 2:
        return None, []
    header = _split_table_row(lines[0])
    sep = _split_table_row(lines[1])
    if not header or len(header) < 2:
        return None, []
    if not sep or not all(re.match(r"^:?-+:?$", c) for c in sep if c):
        return None, []
    rows: list[list[str]] = []
    for line in lines[2:]:
        if not line.strip().startswith("|"):
            break
        row = _split_table_row(line)
        if len(row) == len(header):
            rows.append(row)
    return header, rows


def _section_lines_after_heading(text: str, req_id: str) -> list[str]:
    """Linhas até ao próximo `###` de nível equivalente."""
    lines = text.splitlines()
    in_section = False
    collected: list[str] = []
    for line in lines:
        if line.strip().startswith("### ") and f"`{req_id}`" in line:
            in_section = True
            continue
        if in_section:
            if line.strip().startswith("### ") and "`REQ-" in line:
                break
            collected.append(line)
    return collected


def extract_journey_sections(prd_files: list[Path]) -> list[JourneySection]:
    """Extrai tabelas de jornada (passos) sob `### `REQ-JOR-*`."""
    sections: list[JourneySection] = []
    for path in prd_files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for req_id in sorted(set(REQ_RE.findall(text))):
            if not req_id.startswith("REQ-JOR-"):
                continue
            block = _section_lines_after_heading(text, req_id)
            if not block:
                continue
            # primeira tabela no bloco
            table_start = None
            for i, line in enumerate(block):
                if line.strip().startswith("|"):
                    table_start = i
                    break
            if table_start is None:
                continue
            tbl_lines: list[str] = []
            for line in block[table_start:]:
                if line.strip().startswith("|"):
                    tbl_lines.append(line)
                elif tbl_lines:
                    break
            header, rows = _parse_gfm_table(tbl_lines)
            if not header or not rows:
                continue
            lower = [h.lower() for h in header]
            steps: list[dict[str, str]] = []
            for row in rows:
                if len(row) != len(header):
                    continue
                rec = dict(zip(lower, row, strict=True))
                steps.append(rec)
            sections.append(
                JourneySection(
                    req_id=req_id,
                    source_file=path.as_posix(),
                    steps=steps,
                )
            )
    return sections
