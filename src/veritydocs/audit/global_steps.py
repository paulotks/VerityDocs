"""Auditoria global: Steps 2-4 (cross-module, cobertura de decisões, cobertura de fluxos)."""

from __future__ import annotations

from pathlib import Path

from veritydocs.audit.schemas import Finding
from veritydocs.config import ModuleMapping
from veritydocs.traceability.parser import (
    DEC_RE,
    FUNC_REQ_RE,
    REQ_RE,
    parse_dec_ids_from_files,
    parse_rastreio,
    parse_req_ids,
)


def build_req_owner_map(repo_root: Path, modules: list[ModuleMapping]) -> dict[str, str]:
    """Mapeia cada REQ-* ao module_id do PRD onde o ID aparece (primeiro PRD ganha)."""
    req_to_mod: dict[str, str] = {}
    for mod in modules:
        prd = repo_root / mod.prd_path
        if not prd.exists():
            continue
        for x in parse_req_ids([prd]):
            req_to_mod.setdefault(x.req_id, mod.module_id)
    return req_to_mod


def audit_cross_module(repo_root: Path, modules: list[ModuleMapping]) -> list[Finding]:
    """
    Step 2: consistência entre módulos — SPEC referencia REQ de outro PRD sem linha Rastreio PRD.
    """
    owner = build_req_owner_map(repo_root, modules)
    findings: list[Finding] = []
    n = 0
    for mod in modules:
        spec_paths = [repo_root / p for p in mod.spec_primary] + [
            repo_root / s.path for s in mod.spec_secondary
        ]
        for spec_path in spec_paths:
            if not spec_path.exists():
                continue
            try:
                text = spec_path.read_text(encoding="utf-8")
            except OSError:
                continue
            mentioned = set(REQ_RE.findall(text))
            traced = {t.req_id for t in parse_rastreio([spec_path])}
            for req_id in sorted(mentioned):
                home = owner.get(req_id)
                if home is None or home == mod.module_id:
                    continue
                if req_id not in traced:
                    n += 1
                    findings.append(
                        Finding(
                            id=f"XMOD-{n:03d}",
                            severity="importante",
                            type="cross_module_sem_rastreio",
                            req_ids=[req_id],
                            descricao=(
                                f"SPEC do modulo {mod.module_id} "
                                f"({spec_path.relative_to(repo_root)}) "
                                f"referencia {req_id} "
                                f"definido no PRD do modulo {home} "
                                f"sem entrada em linha 'Rastreio PRD' / "
                                f"'PRD trace' neste ficheiro."
                            ),
                        )
                    )
    return findings


def _collect_spec_files_for_decisions(docs_root: Path, modules: list[ModuleMapping]) -> list[Path]:
    """Todos os ficheiros SPEC conhecidos no mapeamento + markdown em docs/SPEC/."""
    seen: set[Path] = set()
    root = docs_root.parent
    for mod in modules:
        for rel in mod.spec_primary:
            p = root / rel
            if p.is_file():
                seen.add(p.resolve())
        for sec in mod.spec_secondary:
            p = root / sec.path
            if p.is_file():
                seen.add(p.resolve())
    spec_dir = docs_root / "SPEC"
    if spec_dir.is_dir():
        for p in spec_dir.rglob("*.md"):
            if p.is_file():
                seen.add(p.resolve())
    return sorted(seen)


def audit_decision_coverage(
    docs_root: Path, modules: list[ModuleMapping]
) -> list[Finding]:
    """
    Step 3: decisões em audit/decisions-log.md referenciadas em pelo menos um ficheiro SPEC.
    """
    log_path = docs_root / "audit" / "decisions-log.md"
    if not log_path.is_file():
        return []
    try:
        log_text = log_path.read_text(encoding="utf-8")
    except OSError:
        return []
    decs_in_log = set(DEC_RE.findall(log_text))
    if not decs_in_log:
        return []

    spec_files = _collect_spec_files_for_decisions(docs_root, modules)
    decs_in_spec = set(parse_dec_ids_from_files(spec_files))
    missing = sorted(decs_in_log - decs_in_spec)
    findings: list[Finding] = []
    for i, dec_id in enumerate(missing, start=1):
        findings.append(
            Finding(
                id=f"DEC-COV-{i:03d}",
                severity="bloqueante",
                type="decisao_sem_referencia_spec",
                req_ids=[dec_id],
                descricao=(
                    f"Decisao {dec_id} registada em audit/decisions-log.md sem referencia "
                    f"em ficheiros SPEC."
                ),
            )
        )
    return findings


def _collect_func_reqs_from_prd(docs_root: Path) -> set[str]:
    prd_dir = docs_root / "PRD"
    out: set[str] = set()
    if not prd_dir.is_dir():
        return out
    for p in prd_dir.rglob("*.md"):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        out.update(FUNC_REQ_RE.findall(text))
    return out


def _collect_func_reqs_covered_in_flows(docs_root: Path) -> set[str]:
    flows_dir = docs_root / "flows"
    covered: set[str] = set()
    if not flows_dir.is_dir():
        return covered
    for p in flows_dir.rglob("*.md"):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        covered.update(FUNC_REQ_RE.findall(text))
    return covered


def audit_flow_coverage(docs_root: Path) -> list[Finding]:
    """
    Step 4: cada REQ-FUNC-* presente no PRD deve aparecer em docs/flows/ (rastreio de fluxo).
    """
    func_reqs = _collect_func_reqs_from_prd(docs_root)
    if not func_reqs:
        return []

    covered = _collect_func_reqs_covered_in_flows(docs_root)
    missing = sorted(func_reqs - covered)
    findings: list[Finding] = []
    for i, req_id in enumerate(missing, start=1):
        findings.append(
            Finding(
                id=f"FLOW-COV-{i:03d}",
                severity="importante",
                type="req_func_sem_fluxo",
                req_ids=[req_id],
                descricao=(
                    f"Requisito funcional {req_id} presente no PRD sem referencia em docs/flows/ "
                    f"(inclua o ID do requisito num diagrama ou texto de fluxo)."
                ),
            )
        )
    return findings
