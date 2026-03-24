"""Esquema e validação de `veritydocs/workflows.yaml`.

Catálogo canónico de mudanças documentais.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from veritydocs.toolgen.canonical_render import CANONICAL_WORKFLOW_IDS

ARTIFACT_IDS = frozenset({"proposal", "design", "tasks", "metadata"})
DELTA_MODES = frozenset({"none", "optional", "required"})
VERIFY_RULE_IDS = frozenset(
    {
        "task_refs_required",
        "trace_after_apply",
        "check_after_apply",
        "flows_after_flow_change",
        "decisions_audit_after_decision",
    }
)
REQUIRED_CHANGE_TYPE_KEYS = frozenset(
    {
        "requirement",
        "architecture",
        "flow",
        "criteria",
        "decision",
        "restructure",
        "stack",
    }
)


class ProfileEntry(BaseModel):
    active: list[str]


ORDER_STEP_IDS = frozenset({"apply", "archive"})


class ChangeTypeEntry(BaseModel):
    """Regras por tipo de mudança (artefactos, verify, delta / strict-change)."""

    artifacts: list[str]
    order: list[str] = Field(default_factory=list)
    verify_rules: list[str] = Field(default_factory=list)
    delta_mode: Literal["none", "optional", "required"] = "none"
    strict_change_default: bool = False

    @model_validator(mode="after")
    def _defaults_and_refs(self) -> ChangeTypeEntry:
        for a in self.artifacts:
            if a not in ARTIFACT_IDS:
                msg = f"artifact desconhecido: {a!r} (use: {', '.join(sorted(ARTIFACT_IDS))})"
                raise ValueError(msg)
        if not self.artifacts:
            msg = "artifacts nao pode ser vazio"
            raise ValueError(msg)
        order_allowed = ARTIFACT_IDS | ORDER_STEP_IDS
        if not self.order:
            object.__setattr__(self, "order", [*self.artifacts, "apply"])
        else:
            for step in self.order:
                if step not in order_allowed:
                    msg = f"order contém passo desconhecido: {step!r}"
                    raise ValueError(msg)
        for rule in self.verify_rules:
            if rule not in VERIFY_RULE_IDS:
                msg = f"verify_rules contém regra desconhecida: {rule!r}"
                raise ValueError(msg)
        if self.delta_mode not in DELTA_MODES:
            msg = f"delta_mode invalido: {self.delta_mode!r}"
            raise ValueError(msg)
        return self


class WorkflowsSpec(BaseModel):
    """Raiz do ficheiro workflows.yaml."""

    version: str
    profile: Literal["core", "expanded"] = "core"
    default_active: list[str] = Field(default_factory=list)
    change_types: dict[str, ChangeTypeEntry]
    profiles: dict[str, ProfileEntry]
    tasks_template: str = ""

    @model_validator(mode="after")
    def _cross_check(self) -> WorkflowsSpec:
        missing = REQUIRED_CHANGE_TYPE_KEYS - set(self.change_types.keys())
        if missing:
            msg = f"change_types em falta: {', '.join(sorted(missing))}"
            raise ValueError(msg)

        for name, wf_list in (
            ("default_active", self.default_active),
        ):
            for wid in wf_list:
                if wid not in CANONICAL_WORKFLOW_IDS:
                    msg = f"{name} contém workflow desconhecido: {wid!r}"
                    raise ValueError(msg)

        for pname, prof in self.profiles.items():
            for wid in prof.active:
                if wid not in CANONICAL_WORKFLOW_IDS:
                    msg = f"profiles.{pname}.active contém workflow desconhecido: {wid!r}"
                    raise ValueError(msg)

        if self.tasks_template:
            low = self.tasks_template.lower()
            if "file:" not in low or "ids:" not in low:
                msg = "tasks_template deve mencionar `file:` e `ids:` (REQ/DEC, ficheiros)"
                raise ValueError(msg)

        return self


def load_workflows_yaml(path: Path) -> WorkflowsSpec:
    """Carrega e valida o YAML de workflows."""
    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        msg = "O ficheiro workflows deve ser um mapa YAML na raiz."
        raise ValueError(msg)
    return WorkflowsSpec.model_validate(raw)


def validate_workflows_file(path: Path) -> tuple[bool, str]:
    """
    Valida `veritydocs/workflows.yaml`.
    Retorna (True, "") ou (False, mensagem de erro).
    """
    if not path.is_file():
        return False, f"ficheiro em falta: {path.as_posix()}"
    try:
        load_workflows_yaml(path)
    except ValidationError as exc:
        return False, str(exc)
    except ValueError as exc:
        return False, str(exc)
    except yaml.YAMLError as exc:
        return False, f"YAML invalido: {exc}"
    return True, ""


def workflows_check_row(workflows_path: Path) -> tuple[str, str, str]:
    """Uma linha de regra para `run_checks` (rule, status, detail)."""
    ok, err = validate_workflows_file(workflows_path)
    if ok:
        return ("workflows.yaml válido", "OK", "")
    return ("workflows.yaml válido", "ERROR", err)


def parse_workflows_dict(data: dict[str, Any]) -> WorkflowsSpec:
    """Útil em testes — valida um dicionário já carregado."""
    return WorkflowsSpec.model_validate(data)


_TASKS_TEMPLATE = """# tasks.md — checklist documental

Cada tarefa DEVE incluir referências explícitas para rastreio (grafo de artefactos):

- [ ] **Tarefa** — resumo em uma linha
  - `file:` `docs/PRD/03-functional-requirements.md` (ou outro caminho relativo à raiz do projecto)
  - `ids:` REQ-FUNC-001, REQ-FUNC-002, DEC-4 (REQ-*, DEC-*, FLOW-* quando aplicável)
  - `notes:` impacto, dependências, ou ligação a `docs/flows/`, `docs/audit/`

Para mudanças grandes (ex.: reestruturação) ou quando `--strict-change` está activo,
pode usar blocos ADDED/MODIFIED/REMOVED em ficheiros dedicados, conforme
`veritydocs/workflows.yaml` para o tipo.
"""


def canonical_workflows_yaml_text(profile: Literal["core", "expanded"]) -> str:
    """Conteúdo canónico de `veritydocs/workflows.yaml` gerado pelo `veritydocs init`."""
    core_active = ["propose", "apply", "archive"]
    expanded_active = [
        "propose",
        "explore",
        "apply",
        "verify",
        "sync",
        "archive",
        "onboard",
        "lang",
    ]
    active_for_profile = core_active if profile == "core" else expanded_active
    default_lines = "\n".join(f"  - {x}" for x in active_for_profile)

    def _yaml_sublist(xs: list[str]) -> str:
        return "\n".join(f"      - {x}" for x in xs)
    return f"""# VerityDocs — catálogo de workflows e tipos de mudança (edite com a equipa)
# Documentação: cada tipo define artefactos, regras de verify, e política delta / strict-change.

version: "1.0"
profile: {profile}

default_active:
{default_lines}

change_types:
  requirement:
    artifacts: [proposal, design, tasks]
    order: [proposal, design, tasks, apply]
    verify_rules: [task_refs_required, trace_after_apply, check_after_apply]
    delta_mode: none
    strict_change_default: false
  architecture:
    artifacts: [proposal, design, tasks]
    order: [proposal, design, tasks, apply]
    verify_rules: [task_refs_required, trace_after_apply, check_after_apply]
    delta_mode: optional
    strict_change_default: false
  flow:
    artifacts: [proposal, design, tasks]
    order: [proposal, design, tasks, apply]
    verify_rules:
      [task_refs_required, flows_after_flow_change, trace_after_apply, check_after_apply]
    delta_mode: optional
    strict_change_default: false
  criteria:
    artifacts: [proposal, design, tasks]
    order: [proposal, design, tasks, apply]
    verify_rules: [task_refs_required, trace_after_apply, check_after_apply]
    delta_mode: none
    strict_change_default: false
  decision:
    artifacts: [proposal, design, tasks, metadata]
    order: [proposal, design, tasks, apply]
    verify_rules:
      [task_refs_required, decisions_audit_after_decision, trace_after_apply, check_after_apply]
    delta_mode: none
    strict_change_default: false
  restructure:
    artifacts: [proposal, design, tasks]
    order: [proposal, design, tasks, apply]
    verify_rules: [task_refs_required, trace_after_apply, check_after_apply]
    delta_mode: optional
    strict_change_default: true
  stack:
    artifacts: [proposal, design, tasks, metadata]
    order: [proposal, design, tasks, apply]
    verify_rules: [task_refs_required, trace_after_apply, check_after_apply]
    delta_mode: optional
    strict_change_default: false

profiles:
  core:
    active:
{_yaml_sublist(core_active)}
  expanded:
    active:
{_yaml_sublist(expanded_active)}

tasks_template: |
{_indent_block(_TASKS_TEMPLATE)}
"""


def _indent_block(text: str, prefix: str = "  ") -> str:
    lines = text.rstrip().splitlines()
    return "\n".join(prefix + line if line else "" for line in lines)
