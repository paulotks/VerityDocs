from __future__ import annotations

import csv
from io import StringIO

from veritydocs.audit.schemas import ConsolidatedAudit, CoverageRow

CSV_HEADER = ("PRD-ID", "SPEC-Path", "Status", "Severidade", "Comentario")


def render_traceability_csv(rows: list[CoverageRow]) -> str:
    buf = StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for row in rows:
        writer.writerow(
            (row.prd_id, row.spec_path, row.status, row.severidade, row.comentario)
        )
    return buf.getvalue()


def render_module_audit_markdown(audit: ConsolidatedAudit) -> str:
    es = audit.executive_summary
    cov = es.coverage
    lines: list[str] = [
        f"# Auditoria — {audit.module_id}",
        "",
        "## Resumo executivo",
        "",
        f"- Total de findings: **{es.total_findings}** (bloqueantes: {es.bloqueantes}, "
        f"importantes: {es.importantes}, menores: {es.menores})",
        f"- Cobertura PRD→SPEC: coberto {cov.get('coberto', 0)}, parcial {cov.get('parcial', 0)}, "
        f"não coberto {cov.get('nao_coberto', 0)}",
        "",
        "## Findings PRD (órfãos / inconsistências)",
        "",
    ]
    if audit.prd_findings:
        for f in audit.prd_findings:
            reqs = ", ".join(f.req_ids) if f.req_ids else "—"
            lines.append(
                f"- **{f.id}** ({f.severity} / {f.type}) — REQ: {reqs} — {f.descricao}"
            )
    else:
        lines.append("_Nenhum._")
    lines.extend(["", "## Findings SPEC (lacunas)", ""])
    if audit.spec_findings:
        for f in audit.spec_findings:
            reqs = ", ".join(f.req_ids) if f.req_ids else "—"
            lines.append(
                f"- **{f.id}** ({f.severity} / {f.type}) — REQ: {reqs} — {f.descricao}"
            )
    else:
        lines.append("_Nenhum._")
    conflicts = audit.cross_check.blocking_conflicts
    lines.extend(["", "## Conflitos bloqueantes (cross-check)", ""])
    if conflicts:
        for c in conflicts:
            lines.append(f"- {c}")
    else:
        lines.append("_Nenhum._")
    lines.append("")
    return "\n".join(lines)
