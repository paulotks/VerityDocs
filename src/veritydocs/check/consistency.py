from __future__ import annotations

import importlib
import re
from collections.abc import Callable
from pathlib import Path
from typing import cast

from veritydocs.config import compute_config_hash, load_config
from veritydocs.toolgen.artifact_metadata import parse_embedded_meta
from veritydocs.traceability.engine import build_traceability
from veritydocs.workflows_spec import workflows_check_row

REQ_RE = re.compile(r"REQ-[A-Z]+(?:-[A-Z0-9]+)*-\d+")
SPEC_LINK_RE = re.compile(r"->\s*SPEC:\s*\[[^\]]+\]\(([^)]+)\)")
PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|\[PENDENTE\])\b", re.IGNORECASE)
RuleRow = tuple[str, str, str]
RulePlugin = Callable[[Path], list[RuleRow]]


def _load_plugin(spec: str) -> RulePlugin:
    module_name, _, fn_name = spec.partition(":")
    if not module_name or not fn_name:
        raise ValueError(f"Plugin invalido '{spec}'. Use modulo:funcao")
    module = importlib.import_module(module_name)
    fn = getattr(module, fn_name, None)
    if not callable(fn):
        raise ValueError(f"Plugin '{spec}' nao e executavel")
    return cast(RulePlugin, fn)


def _expected_toolgen_paths(project_root: Path, tool_ids: set[str]) -> list[Path]:
    found: set[Path] = set()
    if "cursor" in tool_ids:
        found.update(project_root.glob(".cursor/rules/veritydocs-*.mdc"))
        found.update(project_root.glob(".cursor/commands/vrtdocs-*.md"))
        mcp = project_root / ".cursor" / "mcp.json"
        if mcp.is_file():
            found.add(mcp.resolve())
    if "claude" in tool_ids:
        found.update(project_root.glob(".claude/skills/veritydocs-*.md"))
        claude_md = project_root / "CLAUDE.md"
        if claude_md.is_file():
            found.add(claude_md.resolve())
    return sorted(found)


def _toolgen_config_drift_row(project_root: Path, config_path: Path) -> RuleRow:
    rule = "Artefactos toolgen — drift de config"
    cfg = load_config(config_path)
    if not cfg.tools:
        return (rule, "OK", "")
    tool_ids = {t.strip().lower() for t in cfg.tools}
    expected = _expected_toolgen_paths(project_root, tool_ids)
    if not expected:
        msg = (
            "Ferramentas configuradas em `tools` mas nenhum artefato gerado encontrado; "
            "execute `veritydocs sync`."
        )
        return (rule, "WARN", msg)
    current = compute_config_hash(config_path)
    stale: list[str] = []
    missing_meta: list[str] = []
    for p in expected:
        rel = p.relative_to(project_root.resolve()).as_posix()
        meta = parse_embedded_meta(p)
        if meta is None:
            missing_meta.append(rel)
            continue
        _, embedded_hash = meta
        if embedded_hash != current:
            stale.append(rel)
    parts: list[str] = []
    if stale:
        parts.append(
            "Hash da config difere do embutido em: "
            + ", ".join(stale)
            + ". Execute `veritydocs sync`."
        )
    if missing_meta:
        parts.append(
            "Sem metadados VerityDocs em: "
            + ", ".join(missing_meta)
            + ". Execute `veritydocs sync`."
        )
    if not parts:
        return (rule, "OK", "")
    return (rule, "WARN", " ".join(parts))


def run_checks(
    docs_root: Path,
    strict: bool = False,
    plugins: list[str] | None = None,
    workflows_file: Path | None = None,
    *,
    config_path: Path | None = None,
) -> list[RuleRow]:
    results: list[RuleRow] = []
    prd_files = sorted((docs_root / "PRD").glob("*.md"))
    spec_files = sorted((docs_root / "SPEC").glob("*.md"))

    all_ids: list[str] = []
    for f in prd_files:
        all_ids += REQ_RE.findall(f.read_text(encoding="utf-8"))
    duplicates = sorted({x for x in all_ids if all_ids.count(x) > 1})
    results.append(("REQ unico", "ERROR" if duplicates else "OK", ", ".join(duplicates)))

    trace = build_traceability(docs_root)
    df = trace.dec_flow
    missing_coverage = trace.phantom_ids
    results.append(
        (
            "Cobertura PRD->SPEC",
            "ERROR" if missing_coverage else "OK",
            ", ".join(missing_coverage),
        )
    )
    results.append(
        (
            "IDs orfaos na SPEC",
            "WARN" if trace.orphan_reqs else "OK",
            ", ".join(trace.orphan_reqs),
        )
    )
    results.append(
        (
            "DEC na SPEC sem registo em audit/decisions-log",
            "ERROR" if df.dec_orphan_in_spec else "OK",
            ", ".join(df.dec_orphan_in_spec),
        )
    )
    results.append(
        (
            "DEC no log sem menção na SPEC",
            "WARN" if df.dec_not_in_spec else "OK",
            ", ".join(df.dec_not_in_spec),
        )
    )
    results.append(
        (
            "FLOW na SPEC sem definição em docs/flows",
            "ERROR" if df.flow_orphan_in_spec else "OK",
            ", ".join(df.flow_orphan_in_spec),
        )
    )
    results.append(
        (
            "FLOW em docs/flows sem menção na SPEC",
            "WARN" if df.flow_not_in_spec else "OK",
            ", ".join(df.flow_not_in_spec),
        )
    )

    dead_links: list[str] = []
    for f in prd_files:
        txt = f.read_text(encoding="utf-8")
        for target in SPEC_LINK_RE.findall(txt):
            candidate = (f.parent / target.split("#")[0]).resolve()
            if not candidate.exists():
                dead_links.append(f"{f.name}:{target}")
    results.append(
        ("Links -> SPEC validos", "ERROR" if dead_links else "OK", "; ".join(dead_links))
    )

    for index_name in ["_index.md"]:
        results.append(
            (
                "Index PRD existe",
                "OK" if (docs_root / "PRD" / index_name).exists() else "ERROR",
                "",
            )
        )
        results.append(
            (
                "Index SPEC existe",
                "OK" if (docs_root / "SPEC" / index_name).exists() else "ERROR",
                "",
            )
        )

    map_path = docs_root / "audit" / "step0-module-mapping.json"
    results.append(("Module mapping existe", "OK" if map_path.exists() else "ERROR", ""))

    if config_path is not None and config_path.is_file():
        project_root = config_path.parent.resolve()
        results.append(_toolgen_config_drift_row(project_root, config_path))

    if workflows_file is not None:
        results.append(workflows_check_row(workflows_file))

    if strict:
        pending = []
        for f in [*prd_files, *spec_files]:
            if PLACEHOLDER_RE.search(f.read_text(encoding="utf-8")):
                pending.append(f.name)
        results.append(("Placeholders pendentes", "ERROR" if pending else "OK", ", ".join(pending)))
    else:
        results.append(("Placeholders pendentes", "WARN", "Use --strict para validar"))

    for spec in plugins or []:
        try:
            plugin = _load_plugin(spec)
            results.extend(plugin(docs_root))
        except Exception as exc:
            results.append((f"Plugin {spec}", "ERROR", str(exc)))

    return results
