"""Agregação de estado do projecto e instruções de workflow para a CLI (CLI-as-API)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from veritydocs import __version__
from veritydocs.change_manager import read_metadata
from veritydocs.check.consistency import run_checks
from veritydocs.config import VerityDocsConfig
from veritydocs.skill_evolution import (
    CONTEXT7_MCP_QUERY_DOCS_TOOL,
    CONTEXT7_MCP_RESOLVE_LIBRARY_TOOL,
)
from veritydocs.toolgen.canonical_render import CANONICAL_WORKFLOW_IDS, render_workflow_body
from veritydocs.toolgen.context import GenerationContext
from veritydocs.traceability.engine import build_traceability
from veritydocs.traceability.parser import DEC_RE


def parse_output_format(fmt: str) -> Literal["json", "md"]:
    low = fmt.strip().lower()
    if low == "json":
        return "json"
    if low in ("md", "markdown"):
        return "md"
    msg = f"Formato --format invalido: {fmt!r}. Use json ou md."
    raise ValueError(msg)


def _list_open_changes(changes_dir: Path, docs_root: str) -> list[dict[str, Any]]:
    if not changes_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    dr = docs_root.strip("/").replace("\\", "/")
    for p in sorted(changes_dir.iterdir()):
        if not p.is_dir() or p.name in ("archive",) or p.name.startswith("."):
            continue
        rel_path = f"{dr}/changes/{p.name}"
        out.append(
            {
                "name": p.name,
                "path": rel_path,
                "metadata": read_metadata(p),
            }
        )
    return out


def _archive_folder_count(changes_dir: Path) -> int:
    arch = changes_dir / "archive"
    if not arch.is_dir():
        return 0
    return sum(1 for x in arch.iterdir() if x.is_dir() and not x.name.startswith("."))


def _decisions_snapshot(docs_root: Path) -> dict[str, Any]:
    log = docs_root / "audit" / "decisions-log.md"
    if not log.is_file():
        return {"log_exists": False, "dec_ids": [], "dec_ids_count": 0}
    text = log.read_text(encoding="utf-8")
    ids = sorted(set(DEC_RE.findall(text)))
    return {"log_exists": True, "dec_ids": ids[-20:], "dec_ids_count": len(ids)}


def build_status_payload(
    cfg: VerityDocsConfig,
    cfg_path: Path,
    *,
    change: str | None = None,
) -> dict[str, Any]:
    repo = cfg_path.parent
    docs_root = repo / cfg.docs_root
    changes_dir = docs_root / "changes"

    open_changes = _list_open_changes(changes_dir, cfg.docs_root)
    wf_path = repo / cfg.workflows_file.path
    check_rows = run_checks(
        docs_root,
        strict=False,
        plugins=cfg.check.plugins,
        workflows_file=wf_path,
        config_path=cfg_path,
    )
    trace = build_traceability(docs_root)
    has_error = any(status == "ERROR" for _, status, _ in check_rows)

    payload: dict[str, Any] = {
        "veritydocs_version": __version__,
        "config_path": cfg_path.as_posix(),
        "project": {
            "name": cfg.project.name,
            "language": cfg.project.language,
            "domain": cfg.project.domain,
            "profile": cfg.profile,
            "docs_root": cfg.docs_root,
        },
        "tools": list(cfg.tools),
        "workflows": {
            "active": list(cfg.workflows.active),
            "file": cfg.workflows_file.path,
        },
        "changes": {
            "open": open_changes,
            "archive_folder_count": _archive_folder_count(changes_dir),
        },
        "check": {
            "has_error": has_error,
            "rows": [
                {"rule": rule, "status": status, "detail": detail}
                for rule, status, detail in check_rows
            ],
        },
        "traceability": {
            "matrix_rows": len(trace.matrix),
            "orphan_reqs_count": len(trace.orphan_reqs),
            "phantom_ids_count": len(trace.phantom_ids),
            "dec_orphan_in_spec_count": len(trace.dec_flow.dec_orphan_in_spec),
            "dec_not_in_spec_count": len(trace.dec_flow.dec_not_in_spec),
            "flow_orphan_in_spec_count": len(trace.dec_flow.flow_orphan_in_spec),
            "flow_not_in_spec_count": len(trace.dec_flow.flow_not_in_spec),
        },
        "decisions": _decisions_snapshot(docs_root),
        "focused_change": None,
        "mcp": {
            "context7": {
                "enabled": cfg.mcp.context7.enabled,
                "auto_consult": cfg.mcp.context7.auto_consult,
                "stack": list(cfg.mcp.context7.stack),
                "resolve_tool": CONTEXT7_MCP_RESOLVE_LIBRARY_TOOL,
                "query_tool": CONTEXT7_MCP_QUERY_DOCS_TOOL,
            }
        },
    }

    if change:
        target = changes_dir / change
        if not target.is_dir() or change in ("archive",) or "/" in change or "\\" in change:
            payload["focused_change"] = {
                "name": change,
                "error": "not_found",
                "path": str(Path(cfg.docs_root) / "changes" / change).replace("\\", "/"),
            }
        else:
            payload["focused_change"] = {
                "name": change,
                "path": str(Path(cfg.docs_root) / "changes" / change).replace("\\", "/"),
                "metadata": read_metadata(target),
            }

    return payload


def render_status_markdown(payload: dict[str, Any], lang: str) -> str:
    is_en = lang == "en"
    lines: list[str] = []
    title = "VerityDocs status" if is_en else "Estado VerityDocs"
    lines.append(f"# {title}\n")
    p = payload["project"]
    lines.append("## Project" if is_en else "## Projecto")
    lines.append(f"- **name:** {p['name']}")
    lines.append(f"- **language:** {p['language']}")
    lines.append(f"- **domain:** {p['domain']}")
    lines.append(f"- **profile:** {p['profile']}")
    lines.append(f"- **docs_root:** `{p['docs_root']}`")
    lines.append(f"- **tools:** {', '.join(payload['tools']) or '—'}")
    lines.append(
        f"- **workflows.active:** {', '.join(payload['workflows']['active'])}\n",
    )

    lines.append("## Open changes" if is_en else "## Changes abertos")
    for ch in payload["changes"]["open"]:
        meta = ch.get("metadata")
        status = ""
        if isinstance(meta, dict) and (st := meta.get("status")):
            status = f" — _{st}_"
        lines.append(f"- `{ch['name']}`{status}")
    if not payload["changes"]["open"]:
        lines.append("- —" if is_en else "- (nenhum)")
    lines.append(
        f"\n**archive/** folders: {payload['changes']['archive_folder_count']}\n",
    )

    mcp = payload.get("mcp", {}).get("context7", {})
    if mcp:
        lines.append("## MCP (Context7)")
        lines.append(
            f"- **enabled:** {mcp.get('enabled')}; **auto_consult:** {mcp.get('auto_consult')}",
        )
        st = mcp.get("stack") or []
        lines.append(f"- **stack:** {', '.join(st) if st else '—'}")
        lines.append("")

    lines.append("## Check" if is_en else "## Verificação (check)")
    for row in payload["check"]["rows"]:
        suffix = f" — {row['detail']}" if row["detail"] else ""
        lines.append(f"- **[{row['status']}]** {row['rule']}{suffix}")
    lines.append("")

    t = payload["traceability"]
    lines.append("## Traceability" if is_en else "## Rastreabilidade")
    lines.append(f"- matrix rows: {t['matrix_rows']}")
    lines.append(f"- orphan REQ in SPEC: {t['orphan_reqs_count']}")
    lines.append(f"- phantom / missing SPEC coverage: {t['phantom_ids_count']}")
    lines.append(
        f"- DEC in SPEC without decisions-log entry: {t['dec_orphan_in_spec_count']}",
    )
    lines.append(
        f"- DEC in log without SPEC mention: {t['dec_not_in_spec_count']}",
    )
    lines.append(
        f"- FLOW in SPEC without docs/flows definition: {t['flow_orphan_in_spec_count']}",
    )
    lines.append(
        f"- FLOW in docs/flows without SPEC mention: {t['flow_not_in_spec_count']}\n",
    )

    d = payload["decisions"]
    lines.append("## Decisions log")
    if d.get("log_exists"):
        lines.append(f"- distinct DEC-* (total): {d['dec_ids_count']}")
        if d["dec_ids"]:
            lines.append(f"- sample: {', '.join(d['dec_ids'])}")
    else:
        lines.append("- (log missing)" if is_en else "- (ficheiro em falta)")

    fc = payload.get("focused_change")
    if fc:
        lines.append("\n## Focused change" if is_en else "\n## Change focado")
        lines.append(f"- `{fc['name']}`")
        if fc.get("error") == "not_found":
            lines.append("- **error:** not found" if is_en else "- **erro:** não encontrado")
        elif isinstance(fc.get("metadata"), dict):
            lines.append(f"- metadata: `{json.dumps(fc['metadata'], ensure_ascii=False)}`")

    ver = payload["veritydocs_version"]
    cfg_p = payload["config_path"]
    lines.append(f"\n_config: `{cfg_p}` · VerityDocs {ver}")
    return "\n".join(lines).strip() + "\n"


def build_instructions_payload(
    workflow: str,
    cfg: VerityDocsConfig,
    cfg_path: Path,
    *,
    change: str | None = None,
) -> dict[str, Any]:
    wf = workflow.strip().lower()
    if wf not in CANONICAL_WORKFLOW_IDS:
        valid = ", ".join(CANONICAL_WORKFLOW_IDS)
        msg = f"Workflow desconhecido: {workflow!r}. Válidos: {valid}"
        raise ValueError(msg)

    ctx = GenerationContext(
        project_dir=cfg_path.parent.resolve(),
        project_name=cfg.project.name,
        language=cfg.project.language,
        domain=str(cfg.project.domain),
        profile=cfg.profile,
    )
    body = render_workflow_body(wf, ctx)
    docs_root = cfg.docs_root.replace("\\", "/")

    recommended: list[str] = [
        "veritydocs status --format json",
    ]
    if wf in ("apply", "archive", "verify"):
        recommended.append("veritydocs check --format json")
    if wf in ("apply", "verify", "archive"):
        recommended.append("veritydocs trace --format json")
    if wf == "verify":
        recommended.append("veritydocs audit --all")

    payload: dict[str, Any] = {
        "workflow": wf,
        "change": change,
        "project_language": cfg.project.language,
        "profile": cfg.profile,
        "docs_root": docs_root,
        "workflows_active": list(cfg.workflows.active),
        "workflows_file": cfg.workflows_file.path,
        "body_markdown": body,
        "recommended_cli": recommended,
        "mcp": {
            "context7": {
                "enabled": cfg.mcp.context7.enabled,
                "auto_consult": cfg.mcp.context7.auto_consult,
                "stack": list(cfg.mcp.context7.stack),
                "resolve_tool": CONTEXT7_MCP_RESOLVE_LIBRARY_TOOL,
                "query_tool": CONTEXT7_MCP_QUERY_DOCS_TOOL,
            }
        },
    }
    return payload


def render_instructions_markdown(payload: dict[str, Any]) -> str:
    wf = payload["workflow"]
    lines = [
        f"# Instructions: vrtdocs:{wf}",
        "",
        f"- **docs_root:** `{payload['docs_root']}`",
        f"- **profile:** {payload['profile']}",
        f"- **workflows.active:** {', '.join(payload['workflows_active'])}",
    ]
    if payload.get("change"):
        lines.append(f"- **change:** `{payload['change']}`")
    mcp = payload.get("mcp", {}).get("context7", {})
    if mcp:
        lines.append(
            f"- **mcp.context7:** enabled={mcp.get('enabled')}, "
            f"auto_consult={mcp.get('auto_consult')}, "
            f"stack={mcp.get('stack') or []}",
        )
    lines.append("\n## Recommended CLI\n")
    for cmd in payload["recommended_cli"]:
        lines.append(f"- `{cmd}`")
    lines.append("\n---\n")
    lines.append(payload["body_markdown"])
    return "\n".join(lines).strip() + "\n"
