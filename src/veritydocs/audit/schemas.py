from __future__ import annotations

from pydantic import BaseModel, Field


class Finding(BaseModel):
    id: str
    severity: str
    type: str
    req_ids: list[str] = Field(default_factory=list)
    descricao: str


class CoverageRow(BaseModel):
    prd_id: str
    spec_path: str
    status: str
    severidade: str
    comentario: str


class ExecutiveSummary(BaseModel):
    total_findings: int = 0
    bloqueantes: int = 0
    importantes: int = 0
    menores: int = 0
    coverage: dict[str, int] = Field(
        default_factory=lambda: {
            "coberto": 0,
            "parcial": 0,
            "nao_coberto": 0,
        }
    )


class CrossCheck(BaseModel):
    coverage_rows: list[CoverageRow] = Field(default_factory=list)
    blocking_conflicts: list[str] = Field(default_factory=list)


class ConsolidatedAudit(BaseModel):
    module_id: str
    prd_findings: list[Finding] = Field(default_factory=list)
    spec_findings: list[Finding] = Field(default_factory=list)
    cross_check: CrossCheck = Field(default_factory=CrossCheck)
    executive_summary: ExecutiveSummary = Field(default_factory=ExecutiveSummary)
