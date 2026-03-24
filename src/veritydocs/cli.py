from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Literal, cast

import typer
import yaml
from pydantic import ValidationError
from rich import print
from rich.logging import RichHandler

from veritydocs import __version__
from veritydocs.audit.auditor import audit_module
from veritydocs.audit.consolidator import consolidate_global
from veritydocs.audit.global_steps import (
    audit_cross_module,
    audit_decision_coverage,
    audit_flow_coverage,
)
from veritydocs.audit.module_map import load_module_mapping, validate_mapping_files
from veritydocs.audit.reporters import render_module_audit_markdown, render_traceability_csv
from veritydocs.change_manager import archive_change, create_change, mark_applied
from veritydocs.check.consistency import run_checks
from veritydocs.cli_status import (
    build_instructions_payload,
    build_status_payload,
    parse_output_format,
    render_instructions_markdown,
    render_status_markdown,
)
from veritydocs.config import (
    VerityDocsConfig,
    compute_config_hash,
    load_config,
    resolve_config_path,
)
from veritydocs.flows.engine import generate_prd_flows, result_to_json
from veritydocs.i18n import tr
from veritydocs.intake.classifier import classify_requirement
from veritydocs.intake.draft import load_draft, new_draft, save_draft
from veritydocs.intake.interview import QUESTIONS
from veritydocs.intake.similarity import find_similar
from veritydocs.scaffold.generator import init_project
from veritydocs.scaffold.tool_selector import select_tools
from veritydocs.toolgen.context import GenerationContext
from veritydocs.toolgen.generator import generate_tool_artifacts
from veritydocs.traceability.engine import build_traceability
from veritydocs.traceability.reporter import render_json, render_markdown, write_report
from veritydocs.workflows_spec import validate_workflows_file

app = typer.Typer(help="CLI do VerityDocs")
workflows_app = typer.Typer(help="Catálogo veritydocs/workflows.yaml")
app.add_typer(workflows_app, name="workflows")
flows_app = typer.Typer(help="Diagramas Mermaid derivados do PRD")
app.add_typer(flows_app, name="flows")

change_app = typer.Typer(help="Gestao de mudancas documentais (docs/changes).")

LOGGER = logging.getLogger("veritydocs")


def _setup_logging(verbose: bool, quiet: bool) -> None:
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(markup=True, rich_tracebacks=False)],
    )


def _load_config_safe(path: Path | None) -> VerityDocsConfig:
    cfg_path = resolve_config_path(path)
    try:
        return load_config(cfg_path)
    except FileNotFoundError as exc:
        print(f"[red]Erro:[/red] {tr('pt-BR', 'error_config_not_found', path=cfg_path.as_posix())}")
        raise typer.Exit(2) from exc
    except json.JSONDecodeError as exc:
        detail = f"{exc.msg} (linha {exc.lineno})"
        message = tr(
            "pt-BR",
            "error_invalid_json",
            path=cfg_path.as_posix(),
            detail=detail,
        )
        print(f"[red]Erro:[/red] {message}")
        raise typer.Exit(2) from exc
    except yaml.YAMLError as exc:
        message = tr(
            "pt-BR",
            "error_invalid_yaml",
            path=cfg_path.as_posix(),
            detail=str(exc),
        )
        print(f"[red]Erro:[/red] {message}")
        raise typer.Exit(2) from exc
    except ValidationError as exc:
        message = tr(
            "pt-BR",
            "error_validation",
            path=cfg_path.as_posix(),
            detail=str(exc),
        )
        print(f"[red]Erro:[/red] {message}")
        raise typer.Exit(2) from exc
    except ValueError as exc:
        message = tr(
            "pt-BR",
            "error_validation",
            path=cfg_path.as_posix(),
            detail=str(exc),
        )
        print(f"[red]Erro:[/red] {message}")
        raise typer.Exit(2) from exc


def _fail_runtime(lang: str, exc: Exception) -> None:
    LOGGER.debug("Erro interno", exc_info=exc)
    print(f"[red]Erro:[/red] {tr(lang, 'error_generic', detail=str(exc))}")
    raise typer.Exit(1) from exc


def _resolve_lang(config_path: Path | None = None) -> str:
    try:
        cfg_path = resolve_config_path(config_path)
        cfg = load_config(cfg_path)
        return cfg.project.language
    except Exception:
        return "pt-BR"


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    quiet: bool = typer.Option(False, "--quiet", "-q"),
    no_color: bool = typer.Option(False, "--no-color"),
) -> None:
    _setup_logging(verbose=verbose, quiet=quiet)
    if no_color:
        LOGGER.debug("Execucao com --no-color")
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    if version:
        print(tr("pt-BR", "version_label", version=__version__))
        raise typer.Exit(0)


@app.command()
def init(
    name: str = typer.Option("MeuProjeto", "--name"),
    domain: str = typer.Option("software", "--domain"),
    language: str = typer.Option("pt-BR", "--language", "--lang"),
    dir: Path = typer.Option(Path("."), "--dir"),
    tools: str | None = typer.Option(
        None,
        "--tools",
        help="Lista separada por virgulas (ex.: cursor,claude)",
    ),
    profile: str = typer.Option("core", "--profile", help="core | expanded"),
) -> None:
    try:
        if profile not in ("core", "expanded"):
            print(f"[red]Erro:[/red] --profile deve ser core ou expanded (recebido: {profile})")
            raise typer.Exit(2)
        profile_lit = cast(Literal["core", "expanded"], profile)
        try:
            chosen_tools = select_tools(dir.resolve(), tools)
        except ValueError as exc:
            print(f"[red]Erro:[/red] {exc}")
            raise typer.Exit(2) from None
        created = init_project(
            dir.resolve(),
            name,
            language,
            domain,
            chosen_tools,
            profile=profile_lit,
        )
        print(f"[green]{tr(language, 'init_done')}[/green]")
        for p in created:
            print(f"- {p.as_posix()}")
    except typer.Exit:
        raise
    except Exception as exc:
        _fail_runtime(language, exc)


@app.command()
def status(
    config: Path | None = typer.Option(None, "--config", "-c"),
    change: str | None = typer.Option(None, "--change"),
    format: str = typer.Option("json", "--format", help="json | md"),
) -> None:
    lang = _resolve_lang(config)
    try:
        fmt = parse_output_format(format)
    except ValueError as exc:
        print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(2) from exc
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        payload = build_status_payload(cfg, cfg_path, change=change)
        if fmt == "json":
            sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        else:
            print(render_status_markdown(payload, cfg.project.language))
        fc = payload.get("focused_change")
        if (
            change
            and isinstance(fc, dict)
            and fc.get("error") == "not_found"
        ):
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as exc:
        _fail_runtime(lang, exc)


@app.command()
def instructions(
    workflow: str = typer.Argument(..., help="propose, apply, verify, sync, ..."),
    config: Path | None = typer.Option(None, "--config", "-c"),
    change: str | None = typer.Option(None, "--change"),
    format: str = typer.Option("json", "--format", help="json | md"),
) -> None:
    lang = _resolve_lang(config)
    try:
        fmt = parse_output_format(format)
    except ValueError as exc:
        print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(2) from exc
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        payload = build_instructions_payload(workflow, cfg, cfg_path, change=change)
        if fmt == "json":
            sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        else:
            print(render_instructions_markdown(payload))
    except ValueError as exc:
        print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(2) from exc
    except typer.Exit:
        raise
    except Exception as exc:
        _fail_runtime(lang, exc)


@change_app.command("create")
def change_create(
    slug: str = typer.Argument(..., help="Identificador kebab-case (ex.: tactical-ddd)"),
    config: Path | None = typer.Option(None, "--config", "-c"),
    change_type: str = typer.Option(
        "requirement",
        "--type",
        "-t",
        help="requirement | architecture | flow | criteria | decision | restructure | stack",
    ),
    author: str = typer.Option("", "--author"),
    tool: str = typer.Option("", "--tool"),
    summary: str = typer.Option("", "--summary"),
    skill_evolution: bool = typer.Option(False, "--skill-evolution"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    lang = _resolve_lang(config)
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        result = create_change(
            cfg_path.parent,
            cfg.docs_root,
            slug,
            change_type=change_type,
            author=author,
            tool=tool,
            summary=summary,
            skill_evolution=skill_evolution,
            language=cfg.project.language,
            force=force,
        )
        rel = result.change_dir.relative_to(cfg_path.parent.resolve())
        print(
            f"[green]{tr(lang, 'change_create_done', slug=slug, path=rel.as_posix())}[/green]",
        )
    except typer.Exit:
        raise
    except FileExistsError as exc:
        print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(2) from exc
    except ValueError as exc:
        print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(2) from exc
    except Exception as exc:
        _fail_runtime(lang, exc)


@change_app.command("mark-applied")
def change_mark_applied_cmd(
    slug: str = typer.Argument(...),
    config: Path | None = typer.Option(None, "--config", "-c"),
) -> None:
    lang = _resolve_lang(config)
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        mark_applied(cfg_path.parent, cfg.docs_root, slug)
        print(f"[green]{tr(lang, 'change_mark_applied_done', slug=slug)}[/green]")
    except typer.Exit:
        raise
    except FileNotFoundError as exc:
        print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(1) from exc
    except ValueError as exc:
        print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(2) from exc
    except Exception as exc:
        _fail_runtime(lang, exc)


@change_app.command("archive")
def change_archive_cmd(
    slug: str = typer.Argument(...),
    config: Path | None = typer.Option(None, "--config", "-c"),
    summary: str = typer.Option("", "--summary"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    lang = _resolve_lang(config)
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        dest = archive_change(
            cfg_path.parent,
            cfg.docs_root,
            slug,
            force=force,
            readme_summary=summary,
            language=cfg.project.language,
        )
        rel = dest.relative_to(cfg_path.parent.resolve())
        print(f"[green]{tr(lang, 'change_archive_done', path=rel.as_posix())}[/green]")
    except typer.Exit:
        raise
    except FileNotFoundError as exc:
        print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(1) from exc
    except (FileExistsError, ValueError) as exc:
        print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(2) from exc
    except Exception as exc:
        _fail_runtime(lang, exc)


@flows_app.command("generate")
def flows_generate(
    config: Path | None = typer.Option(None, "--config", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Nao escreve ficheiros"),
    format: str = typer.Option("text", "--format", help="text | json"),
) -> None:
    lang = _resolve_lang(config)
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        docs_root = cfg_path.parent / cfg.docs_root
        if cfg.flows.engine not in ("prd", "none"):
            print(
                f"[yellow]{tr(lang, 'flows_engine_config', engine=cfg.flows.engine)}[/yellow]"
            )
        result = generate_prd_flows(
            docs_root,
            dry_run=dry_run,
            lang=cfg.project.language,
        )
        if format == "json":
            sys.stdout.write(result_to_json(result))
        else:
            if result.warnings:
                for w in result.warnings:
                    print(f"[yellow]{tr(lang, 'flows_warning', code=w)}[/yellow]")
            if dry_run:
                print(tr(lang, "flows_dry_run", count=str(result.functional_count)))
                raise typer.Exit(0)
            print(
                tr(
                    lang,
                    "flows_done",
                    n_func=str(result.functional_count),
                    n_j=str(result.journey_sections),
                )
            )
            for wpath in result.written:
                rel = Path(wpath).resolve().relative_to(cfg_path.parent.resolve())
                print(f"- {rel.as_posix()}")
    except typer.Exit:
        raise
    except Exception as exc:
        _fail_runtime(lang, exc)


@app.command()
def sync(
    config: Path | None = typer.Option(None, "--config", "-c"),
) -> None:
    lang = _resolve_lang(config)
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        if not cfg.tools:
            print(f"[yellow]{tr(lang, 'sync_no_tools')}[/yellow]")
            raise typer.Exit(0)
        gen_ctx = GenerationContext(
            project_dir=cfg_path.parent.resolve(),
            project_name=cfg.project.name,
            language=cfg.project.language,
            domain=str(cfg.project.domain),
            profile=cfg.profile,
            config_hash=compute_config_hash(cfg_path),
        )
        written = generate_tool_artifacts(gen_ctx, cfg.tools)
        print(f"[green]{tr(lang, 'sync_done', count=str(len(written)))}[/green]")
        for p in written:
            rel = p.resolve().relative_to(cfg_path.parent.resolve())
            print(f"- {rel.as_posix()}")
    except typer.Exit:
        raise
    except Exception as exc:
        _fail_runtime(lang, exc)


@app.command()
def trace(
    config: Path | None = typer.Option(None, "--config", "-c"),
    format: str = typer.Option("markdown", "--format"),
    output: Path | None = typer.Option(None, "--output"),
) -> None:
    lang = _resolve_lang(config)
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        docs_root = cfg_path.parent / cfg.docs_root
        report = build_traceability(docs_root)
        if format == "json":
            content = render_json(report)
        elif format == "csv":
            lines = ["req_id,prd,spec,notes"]
            for row in report.matrix:
                lines.append(
                    ",".join(
                        [
                            row["req_id"],
                            row["prd"].replace(",", ";"),
                            row["spec"].replace(",", ";"),
                            row["notes"],
                        ]
                    )
                )
            content = "\n".join(lines) + "\n"
        else:
            content = render_markdown(report)
        if output:
            write_report(output, content)
        elif format == "markdown":
            write_report(docs_root / "traceability.md", content)
        print(content)
    except typer.Exit:
        raise
    except Exception as exc:
        _fail_runtime(lang, exc)


@workflows_app.command("validate")
def workflows_validate(
    config: Path | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Valida workflows.yaml (tipos de mudança, delta/strict-change, template de tasks)."""
    lang = _resolve_lang(config)
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        wf = cfg_path.parent / cfg.workflows_file.path
        ok, detail = validate_workflows_file(wf)
        if ok:
            print(f"[green]{tr(lang, 'workflows_validate_ok', path=wf.as_posix())}[/green]")
            raise typer.Exit(0)
        msg = tr(lang, "workflows_validate_fail", path=wf.as_posix(), detail=detail)
        print(f"[red]{msg}[/red]")
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as exc:
        _fail_runtime(lang, exc)


@app.command()
def check(
    config: Path | None = typer.Option(None, "--config", "-c"),
    format: str = typer.Option("text", "--format"),
    strict: bool = typer.Option(False, "--strict"),
    watch: bool = typer.Option(False, "--watch"),
    interval: float = typer.Option(2.0, "--interval"),
) -> None:
    lang = _resolve_lang(config)
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)

        def _run_once() -> int:
            wf_path = cfg_path.parent / cfg.workflows_file.path
            rows = run_checks(
                cfg_path.parent / cfg.docs_root,
                strict=strict,
                plugins=cfg.check.plugins,
                workflows_file=wf_path,
                config_path=cfg_path,
            )
            has_error = any(status == "ERROR" for _, status, _ in rows)
            if format == "json":
                payload = [
                    {"rule": rule, "status": status, "detail": detail}
                    for rule, status, detail in rows
                ]
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                for rule, status, detail in rows:
                    print(f"[{status}] {rule}" + (f" - {detail}" if detail else ""))
            return 1 if has_error else 0

        if watch:
            print("[cyan]Watch mode ativo. Pressione Ctrl+C para parar.[/cyan]")
            try:
                while True:
                    code = _run_once()
                    print(f"[dim]Novo ciclo em {interval:.1f}s. Ultimo status: {code}[/dim]")
                    time.sleep(interval)
            except KeyboardInterrupt as exc:
                raise typer.Exit(0) from exc
        raise typer.Exit(_run_once())
    except typer.Exit:
        raise
    except Exception as exc:
        _fail_runtime(lang, exc)


@app.command()
def audit(
    module_id: str | None = typer.Argument(None),
    config: Path | None = typer.Option(None, "--config", "-c"),
    all: bool = typer.Option(False, "--all"),
    output_dir: Path | None = typer.Option(None, "--output-dir"),
) -> None:
    lang = _resolve_lang(config)
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        repo_root = cfg_path.parent
        mapping_path = repo_root / cfg.docs_root / "audit" / "step0-module-mapping.json"
        modules = load_module_mapping(mapping_path)
        errors = validate_mapping_files(repo_root / cfg.docs_root, modules)
        if errors:
            for err in errors:
                print(f"[ERROR] {err}")
            raise typer.Exit(1)
        out = output_dir or (repo_root / cfg.audit.output_dir)
        targets = modules if all else [m for m in modules if m.module_id == module_id]
        if not targets:
            print(f"[ERROR] {tr(lang, 'module_not_found', module_id=module_id or '<none>')}")
            raise typer.Exit(1)
        json_paths = []
        for mod in targets:
            result = audit_module(repo_root, mod)
            mod_dir = out / mod.module_id
            mod_dir.mkdir(parents=True, exist_ok=True)
            p = mod_dir / "consolidated.json"
            p.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            (mod_dir / "traceability.csv").write_text(
                render_traceability_csv(result.cross_check.coverage_rows),
                encoding="utf-8",
            )
            (mod_dir / "audit-summary.md").write_text(
                render_module_audit_markdown(result),
                encoding="utf-8",
            )
            json_paths.append(p)
            print(f"[OK] auditado {mod.module_id}")
        if all:
            docs_root = repo_root / cfg.docs_root
            cross = audit_cross_module(repo_root, modules)
            dec = audit_decision_coverage(docs_root, modules)
            flow = audit_flow_coverage(docs_root)
            consolidate_global(
                json_paths,
                out / "global" / "consolidated-global.json",
                cross_module_findings=[f.model_dump() for f in cross],
                decision_findings=[f.model_dump() for f in dec],
                flow_findings=[f.model_dump() for f in flow],
            )
            total_g = len(cross) + len(dec) + len(flow)
            if total_g:
                print(
                    f"[dim]Pipeline global (steps 2-4): "
                    f"cross-module={len(cross)}, decisoes={len(dec)}, fluxos={len(flow)}[/dim]"
                )
    except typer.Exit:
        raise
    except Exception as exc:
        _fail_runtime(lang, exc)


@app.command()
def intake(
    config: Path | None = typer.Option(None, "--config", "-c"),
    resume: Path | None = typer.Option(None, "--resume"),
    batch: bool = typer.Option(False, "--batch"),
) -> None:
    lang = _resolve_lang(config)
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        draft = load_draft(resume) if resume else new_draft()

        if batch:
            payload = json.loads(sys.stdin.read() or "{}")
            description = str(payload.get("description", "")).strip()
            if not description:
                print(f"[red]Erro:[/red] {tr(lang, 'batch_input_invalid')}")
                raise typer.Exit(2)
            draft["fields"]["tipo"] = classify_requirement(description)
            draft["fields"]["descricao"] = description
            for key, _ in QUESTIONS[1:]:
                if key in payload:
                    draft["fields"][key] = str(payload[key])
            draft["confirmed"] = bool(payload.get("confirmed", True))
            draft["status"] = "completo" if draft["confirmed"] else "cancelado"
        else:
            description = typer.prompt("Descreva o requisito em linguagem humana")
            draft["fields"]["tipo"] = classify_requirement(description)
            draft["fields"]["descricao"] = description

            docs_text = ""
            docs_root = cfg_path.parent / cfg.docs_root
            for p in (docs_root / "PRD").glob("*.md"):
                docs_text += p.read_text(encoding="utf-8") + "\n"
            similar = find_similar(description, docs_text.splitlines())
            if similar:
                print("[yellow]Possiveis requisitos similares encontrados.[/yellow]")
                print("\n".join(similar[:5]))

            for key, question in QUESTIONS[1:]:
                draft["fields"][key] = typer.prompt(question)
                draft["questions_asked"].append({"field": key, "question": question})

            print("\nEntendi o seguinte requisito. Confirma antes de eu documentar?\n")
            for k, v in draft["fields"].items():
                print(f"- {k}: {v}")
            confirmed = typer.confirm("Confirmar?", default=True)
            draft["confirmed"] = confirmed
            draft["status"] = "completo" if confirmed else "cancelado"

        draft_path = cfg_path.parent / cfg.intake.draft_dir / "intake-draft.json"
        save_draft(draft_path, draft)
        print(tr(lang, "draft_saved", path=draft_path.as_posix()))
    except typer.Exit:
        raise
    except json.JSONDecodeError as exc:
        print(f"[red]Erro:[/red] {tr(lang, 'batch_input_invalid')} ({exc})")
        raise typer.Exit(2) from exc
    except Exception as exc:
        _fail_runtime(lang, exc)


@app.command()
def report(
    config: Path | None = typer.Option(None, "--config", "-c"),
    output: Path = typer.Option(Path("docs/report.html"), "--output"),
) -> None:
    lang = _resolve_lang(config)
    try:
        cfg = _load_config_safe(config)
        cfg_path = resolve_config_path(config)
        docs_root = cfg_path.parent / cfg.docs_root
        report_data = build_traceability(docs_root)
        lines = [
            "<html><head><meta charset='utf-8'><title>VerityDocs Report</title></head><body>",
            "<h1>Relatorio VerityDocs</h1>",
            "<table border='1' cellspacing='0' cellpadding='6'>",
            "<tr><th>REQ</th><th>PRD</th><th>SPEC</th><th>Status</th></tr>",
        ]
        for row in report_data.matrix:
            lines.append(
                f"<tr><td>{row['req_id']}</td><td>{row['prd']}</td><td>{row['spec']}</td><td>{row['notes']}</td></tr>"
            )
        lines += [
            "</table>",
            f"<p>IDs orfaos: {len(report_data.orphan_reqs)}</p>",
            f"<p>IDs sem cobertura: {len(report_data.phantom_ids)}</p>",
            "</body></html>",
        ]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(lines), encoding="utf-8")
        print(tr(lang, "report_html_written", path=output.as_posix()))
    except typer.Exit:
        raise
    except Exception as exc:
        _fail_runtime(lang, exc)


app.add_typer(change_app, name="change")
