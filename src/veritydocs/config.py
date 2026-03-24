"""Configuração do projecto: YAML canónico (`veritydocs.config.yaml`) com fallback JSON legado.

Ordem de resolução em `resolve_config_path`: primeiro ficheiro existente entre
`veritydocs.config.yaml`, `veritydocs.config.yml`, `VerityDocs.config.json`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ProjectConfig(BaseModel):
    name: str
    language: Literal["pt-BR", "en"] = "pt-BR"
    domain: Literal["software", "api", "data-platform", "mobile-app"] = "software"


class ModuleSecondarySpec(BaseModel):
    path: str
    note: str = ""


class ModuleMapping(BaseModel):
    module_id: str
    title: str
    prd_path: str
    spec_primary: list[str] = Field(default_factory=list)
    spec_secondary: list[ModuleSecondarySpec] = Field(default_factory=list)


class AuditConfig(BaseModel):
    severity_threshold: Literal["bloqueante", "importante"] = "bloqueante"
    output_dir: str = "docs/audit/output"


class FlowsConfig(BaseModel):
    """`prd` = geração local a partir de cabeçalhos REQ no PRD; outros valores reservados."""

    engine: Literal["prd", "mcp-mermaid", "mmdc", "none"] = "none"


class IntakeConfig(BaseModel):
    auto_detect_similarity: bool = True
    draft_dir: str = "docs/changes"


class CheckConfig(BaseModel):
    plugins: list[str] = Field(default_factory=list)


class Context7Config(BaseModel):
    enabled: bool = True
    auto_consult: bool = True
    stack: list[str] = Field(default_factory=list)


class MCPConfig(BaseModel):
    context7: Context7Config = Field(default_factory=Context7Config)


class WorkflowsFileConfig(BaseModel):
    """Referência ao ficheiro de workflows na raiz do projeto (veritydocs/workflows.yaml)."""

    path: str = "veritydocs/workflows.yaml"


class WorkflowsRuntimeConfig(BaseModel):
    """Workflows conversacionais activos (perfil core vs expanded)."""

    active: list[str] = Field(default_factory=lambda: ["propose", "apply", "archive"])


class VerityDocsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: str = "1.0"
    project: ProjectConfig
    docs_root: str = "docs"
    tools: list[str] = Field(default_factory=list)
    profile: Literal["core", "expanded"] = "core"
    req_prefixes: list[str] = Field(
        default_factory=lambda: [
            "CTX",
            "OBJ",
            "SCO",
            "RBAC",
            "JOR",
            "FUNC",
            "NFR",
            "ACE",
            "MET",
            "RISK",
        ]
    )
    modules: list[ModuleMapping] = Field(default_factory=list)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    flows: FlowsConfig = Field(default_factory=FlowsConfig)
    intake: IntakeConfig = Field(default_factory=IntakeConfig)
    check: CheckConfig = Field(default_factory=CheckConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    workflows: WorkflowsRuntimeConfig = Field(default_factory=WorkflowsRuntimeConfig)
    workflows_file: WorkflowsFileConfig = Field(default_factory=WorkflowsFileConfig)


CONFIG_FILENAMES = (
    "veritydocs.config.yaml",
    "veritydocs.config.yml",
    "VerityDocs.config.json",
)


def resolve_config_path(explicit: Path | None, cwd: Path | None = None) -> Path:
    """Resolve o ficheiro de config: caminho explícito ou o primeiro existente no cwd."""
    root = cwd or Path.cwd()
    if explicit is not None:
        return explicit.resolve()
    for name in CONFIG_FILENAMES:
        candidate = (root / name).resolve()
        if candidate.is_file():
            return candidate
    return (root / CONFIG_FILENAMES[0]).resolve()


def _strip_utf8_bom(text: str) -> str:
    if text.startswith("\ufeff"):
        return text[1:]
    return text


def _coerce_legacy_config_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Aceita shapes legados (ex.: `workflows` com `path`/`file` embutidos)."""
    wf = data.get("workflows")
    if not isinstance(wf, dict):
        return data
    legacy_path = wf.get("path") or wf.get("file")
    if legacy_path is None or "workflows_file" in data:
        return data
    cleaned = {k: v for k, v in wf.items() if k not in ("path", "file")}
    out = {**data, "workflows": cleaned, "workflows_file": {"path": str(legacy_path)}}
    return out


def _load_raw_config(path: Path) -> dict[str, Any]:
    text = _strip_utf8_bom(path.read_text(encoding="utf-8"))
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            data = json.loads(text)
    if data is None:
        msg = "O ficheiro de config está vazio ou não é um documento válido."
        raise ValueError(msg)
    if not isinstance(data, dict):
        msg = "O ficheiro de config deve ser um objeto na raiz (mapa/dicionario)."
        raise ValueError(msg)
    return data


def load_config(path: Path) -> VerityDocsConfig:
    raw = _coerce_legacy_config_dict(_load_raw_config(path))
    return VerityDocsConfig.model_validate(raw)


def compute_config_hash(path: Path) -> str:
    """SHA-256 (hex) da config efectiva: modelo validado + JSON canónico com chaves ordenadas."""
    raw = _coerce_legacy_config_dict(_load_raw_config(path))
    cfg = VerityDocsConfig.model_validate(raw)
    payload = cfg.model_dump(mode="json", exclude_none=True)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def save_config_yaml(path: Path, cfg: VerityDocsConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = cfg.model_dump(mode="json", exclude_none=True)
    path.write_text(
        yaml.safe_dump(
            payload,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
