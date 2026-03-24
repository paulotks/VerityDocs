from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from veritydocs.config import (
    ModuleMapping,
    ProjectConfig,
    VerityDocsConfig,
    WorkflowsFileConfig,
    WorkflowsRuntimeConfig,
    compute_config_hash,
    save_config_yaml,
)
from veritydocs.i18n.catalog import docs_scaffold, module_titles
from veritydocs.i18n.filenames import docs_templates_dir, load_docs_filemap, normalize_docs_locale
from veritydocs.toolgen.context import GenerationContext
from veritydocs.toolgen.generator import generate_tool_artifacts
from veritydocs.workflows_spec import canonical_workflows_yaml_text

_TEMPLATE_ROOT = Path(__file__).parent / "templates"


def _jinja_env_docs(locale_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(locale_dir.as_posix()),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )


def _jinja_env_domain() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATE_ROOT.as_posix()),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path


_PRD_KEYS = [
    "vision",
    "users_rbac",
    "user_journey",
    "functional",
    "nonfunctional",
    "acceptance",
    "metrics",
]
_SPEC_KEYS = [
    "vision",
    "rbac",
    "state_machines",
    "modules",
    "data_model",
    "backlog",
    "complementary",
]


def _build_modules(
    filemap: dict[str, dict[str, str]], docs_root: str, language: str
) -> list[ModuleMapping]:
    titles = module_titles(language)
    modules: list[ModuleMapping] = []
    for i, prd_key in enumerate(_PRD_KEYS):
        prd_file = filemap["prd"][prd_key]
        sk = _SPEC_KEYS[i]
        spec_file = filemap["spec"][sk]
        mid = f"M{i + 1:02d}"
        modules.append(
            ModuleMapping(
                module_id=mid,
                title=titles[i],
                prd_path=f"{docs_root}/PRD/{prd_file}",
                spec_primary=[f"{docs_root}/SPEC/{spec_file}"],
                spec_secondary=[],
            )
        )
    return modules


def _workflows_active(profile: Literal["core", "expanded"]) -> list[str]:
    if profile == "core":
        return ["propose", "apply", "archive"]
    return ["propose", "explore", "apply", "verify", "sync", "archive", "onboard", "lang"]


def init_project(
    base_dir: Path,
    project_name: str,
    language: str,
    domain: str,
    tools: list[str],
    profile: Literal["core", "expanded"] = "core",
) -> list[Path]:
    """
    Gera a arvore `docs/`, `veritydocs.config.yaml`, `veritydocs/workflows.yaml`
    e artefactos por ferramenta (adaptadores registados).
    """
    locale = normalize_docs_locale(language)
    filemap = load_docs_filemap(locale)
    env_docs = _jinja_env_docs(docs_templates_dir(locale))
    ctx_vars = {"project_name": project_name, "language": language, "domain": domain}

    docs = base_dir / "docs"
    docs_root = "docs"
    created: list[Path] = []

    for section, keys in (("prd", filemap["prd"]), ("spec", filemap["spec"])):
        for key, filename in keys.items():
            tpl_name = f"{section}/{key}.md.j2"
            template = env_docs.get_template(tpl_name)
            out = docs / section.upper() / filename
            created.append(_write(out, template.render(**ctx_vars)))

    domain_tpl = f"{domain}/README.template.md"
    if not (_TEMPLATE_ROOT / domain_tpl).exists():
        domain_tpl = "base/README.template.md"
    readme = _jinja_env_domain().get_template(domain_tpl).render(**ctx_vars)
    created.append(_write(docs / "README.md", readme))

    ds = docs_scaffold(language)
    trace_body = ds.get("trace_header", "") + ds.get(
        "trace_table",
        "| REQ / grupo | PRD | SPEC | Notas |\n|-------------|-----|------|-------|\n",
    )
    created.append(_write(docs / "traceability.md", trace_body))

    created.append(_write(docs / "flows" / "_index.md", ds.get("flows_index", "# Flow index\n")))

    ch_readme = ds.get("changes_readme", "")
    audit_readme = ds.get("audit_readme", "")
    decisions = ds.get("decisions_log", "")

    created.append(_write(docs / "changes" / "README.md", ch_readme))
    created.append(_write(docs / "changes" / "archive" / ".gitkeep", ""))
    created.append(_write(docs / "audit" / "README.md", audit_readme))
    created.append(_write(docs / "audit" / "decisions-log.md", decisions))
    created.append(_write(docs / "audit" / "templates" / ".gitkeep", ""))
    created.append(_write(docs / "audit" / "scripts" / ".gitkeep", ""))
    created.append(_write(docs / "audit" / "output" / ".gitkeep", ""))

    modules = _build_modules(filemap, docs_root, language)
    mapping = {
        "step": "read-indexes",
        "modules": [m.model_dump(mode="json") for m in modules],
    }
    mapping_json = json.dumps(mapping, indent=2, ensure_ascii=False)
    created.append(_write(docs / "audit" / "step0-module-mapping.json", mapping_json))

    wf_dir = base_dir / "veritydocs"
    created.append(_write(wf_dir / "workflows.yaml", canonical_workflows_yaml_text(profile)))

    project = ProjectConfig(name=project_name, language=language, domain=domain)  # type: ignore[arg-type]
    cfg = VerityDocsConfig(
        version="1.0",
        project=project,
        tools=list(dict.fromkeys(tools)),
        profile=profile,
        modules=modules,
        workflows=WorkflowsRuntimeConfig(active=_workflows_active(profile)),
        workflows_file=WorkflowsFileConfig(path="veritydocs/workflows.yaml"),
    )

    config_path = base_dir / "veritydocs.config.yaml"
    save_config_yaml(config_path, cfg)
    created.append(config_path)

    gen_ctx = GenerationContext(
        project_dir=base_dir.resolve(),
        project_name=project_name,
        language=language,
        domain=domain,
        profile=profile,
        config_hash=compute_config_hash(config_path),
    )
    created.extend(generate_tool_artifacts(gen_ctx, tools))

    return created
