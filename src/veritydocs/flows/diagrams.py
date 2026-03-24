from __future__ import annotations

import re
from typing import Literal

from veritydocs.flows.extract import JourneySection, ReqHeading


def _escape_label(text: str, max_len: int = 120) -> str:
    t = text.replace('"', "'").replace("\n", " ").strip()
    if len(t) > max_len:
        t = t[: max_len - 1] + "…"
    return t


def _flowchart_header(kind: Literal["TD", "LR"]) -> str:
    return f"flowchart {kind}"


def build_functional_flowchart(reqs: list[ReqHeading]) -> str:
    """Diagrama em cadeia dos `REQ-FUNC-*` (ordem do PRD)."""
    lines = [_flowchart_header("TD"), "classDef req fill:#e8f4fc,stroke:#0366d6"]
    for i, h in enumerate(reqs):
        nid = f"F{i}"
        label = _escape_label(h.req_id if not h.title else f"{h.req_id}<br/>{h.title}")
        lines.append(f'{nid}["{label}"]:::req')
    for i in range(len(reqs) - 1):
        lines.append(f"  F{i} --> F{i + 1}")
    if not reqs:
        lines.append('  empty["(no REQ-FUNC-* headings found in PRD)"]:::req')
    return "\n".join(lines)


def _pick(row: dict[str, str], *candidates: str) -> str:
    lr = {k.lower(): v for k, v in row.items()}
    for part in candidates:
        for k, v in lr.items():
            if part in k:
                return str(v).strip()
    return ""


def build_journey_flowchart(section: JourneySection) -> str:
    """Um fluxo por secção REQ-JOR-* (passos na ordem da tabela)."""
    safe_id = re.sub(r"[^A-Za-z0-9_]", "_", section.req_id)
    lines = [
        _flowchart_header("TD"),
        f"subgraph {safe_id}[\"{section.req_id}\"]",
        "classDef step fill:#f4f6f8,stroke:#333",
    ]
    for i, row in enumerate(section.steps):
        nid = f"{safe_id}_S{i}"
        step = _pick(row, "step") or str(i + 1)
        actor = _pick(row, "actor")
        touch = _pick(row, "touchpoint", "touch")
        beh = _pick(row, "behaviour", "behavior", "system")
        out = _pick(row, "outcome")
        parts = [f"#{step}"]
        if actor:
            parts.append(actor)
        if touch:
            parts.append(touch)
        if beh:
            parts.append(beh)
        if out:
            parts.append(f"→ {out}")
        label = " — ".join(p for p in parts if p) or f"step {step}"
        lines.append(f'  {nid}["{_escape_label(label)}"]:::step')
    for i in range(len(section.steps) - 1):
        lines.append(f"  {safe_id}_S{i} --> {safe_id}_S{i + 1}")
    lines.append("end")
    return "\n".join(lines)


def wrap_markdown_doc(
    title: str,
    mermaid_body: str,
    *,
    intro: str,
    generated_tag: str,
) -> str:
    return (
        f"# {title}\n\n"
        f"{generated_tag}\n\n"
        f"{intro}\n\n"
        "```mermaid\n"
        f"{mermaid_body}\n"
        "```\n"
    )
