from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def consolidate_global(
    module_json_paths: list[Path],
    output_path: Path,
    *,
    cross_module_findings: list[dict[str, Any]] | None = None,
    decision_findings: list[dict[str, Any]] | None = None,
    flow_findings: list[dict[str, Any]] | None = None,
) -> None:
    modules = []
    for path in module_json_paths:
        modules.append(json.loads(path.read_text(encoding="utf-8")))
    per_module_total = sum(
        m.get("executive_summary", {}).get("total_findings", 0) for m in modules
    )
    s2 = cross_module_findings or []
    s3 = decision_findings or []
    s4 = flow_findings or []
    global_total = len(s2) + len(s3) + len(s4)
    payload = {
        "total_modules": len(modules),
        "aggregate_executive_summary": {
            "total_findings": per_module_total + global_total,
            "per_module_findings": per_module_total,
            "global_pipeline_findings": global_total,
        },
        "modules": modules,
        "pipeline_steps": {
            "step2_cross_module": {"findings": s2, "count": len(s2)},
            "step3_decision_coverage": {"findings": s3, "count": len(s3)},
            "step4_flow_coverage": {"findings": s4, "count": len(s4)},
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
