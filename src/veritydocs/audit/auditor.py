from __future__ import annotations

from pathlib import Path

from veritydocs.audit.schemas import (
    ConsolidatedAudit,
    CoverageRow,
    CrossCheck,
    ExecutiveSummary,
    Finding,
)
from veritydocs.config import ModuleMapping
from veritydocs.traceability.parser import parse_rastreio, parse_req_ids


def audit_module(repo_root: Path, module: ModuleMapping) -> ConsolidatedAudit:
    prd_file = repo_root / module.prd_path
    spec_files = [repo_root / p for p in module.spec_primary] + [
        repo_root / s.path for s in module.spec_secondary
    ]
    reqs = {x.req_id for x in parse_req_ids([prd_file])}
    traces = {x.req_id for x in parse_rastreio([p for p in spec_files if p.exists()])}
    missing = sorted(reqs - traces)
    phantom = sorted(traces - reqs)

    prd_findings: list[Finding] = []
    spec_findings: list[Finding] = []
    rows: list[CoverageRow] = []
    for req in sorted(reqs):
        status = "Coberto" if req in traces else "Não coberto"
        sev = "menor" if status == "Coberto" else "bloqueante"
        rows.append(
            CoverageRow(
                prd_id=req,
                spec_path=";".join(module.spec_primary),
                status=status,
                severidade=sev,
                comentario="",
            )
        )
    for i, req in enumerate(missing, start=1):
        spec_findings.append(
            Finding(
                id=f"SPEC-{module.module_id}-{i:03d}",
                severity="bloqueante",
                type="lacuna",
                req_ids=[req],
                descricao="REQ sem cobertura na SPEC.",
            )
        )
    for i, req in enumerate(phantom, start=1):
        prd_findings.append(
            Finding(
                id=f"PRD-{module.module_id}-{i:03d}",
                severity="importante",
                type="orfao",
                req_ids=[req],
                descricao="ID referenciado na SPEC sem definicao no PRD do modulo.",
            )
        )

    all_findings = [*prd_findings, *spec_findings]
    summary = ExecutiveSummary(
        total_findings=len(all_findings),
        bloqueantes=len([f for f in all_findings if f.severity == "bloqueante"]),
        importantes=len([f for f in all_findings if f.severity == "importante"]),
        menores=len([f for f in all_findings if f.severity == "menor"]),
        coverage={
            "coberto": len([r for r in rows if r.status == "Coberto"]),
            "parcial": 0,
            "nao_coberto": len([r for r in rows if r.status == "Não coberto"]),
        },
    )
    return ConsolidatedAudit(
        module_id=module.module_id,
        prd_findings=prd_findings,
        spec_findings=spec_findings,
        cross_check=CrossCheck(coverage_rows=rows, blocking_conflicts=[]),
        executive_summary=summary,
    )
