"""Testes do esquema e YAML canónico de veritydocs/workflows.yaml."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from veritydocs.workflows_spec import (
    canonical_workflows_yaml_text,
    load_workflows_yaml,
    parse_workflows_dict,
    validate_workflows_file,
)


def test_canonical_yaml_validates_both_profiles(tmp_path: Path) -> None:
    for profile in ("core", "expanded"):
        text = canonical_workflows_yaml_text(profile)  # type: ignore[arg-type]
        p = tmp_path / f"w-{profile}.yaml"
        p.write_text(text, encoding="utf-8")
        spec = load_workflows_yaml(p)
        assert spec.version == "1.0"
        assert spec.profile == profile
        assert "requirement" in spec.change_types
        assert spec.change_types["restructure"].strict_change_default is True
        assert spec.change_types["restructure"].delta_mode == "optional"
        assert spec.change_types["requirement"].delta_mode == "none"
        assert "file:" in spec.tasks_template and "ids:" in spec.tasks_template


def test_validate_workflows_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"
    ok, detail = validate_workflows_file(missing)
    assert ok is False
    assert "ficheiro em falta" in detail or "em falta" in detail


def test_parse_rejects_unknown_verify_rule() -> None:
    raw = {
        "version": "1.0",
        "default_active": ["propose", "apply", "archive"],
        "change_types": {
            "requirement": {
                "artifacts": ["proposal", "design", "tasks"],
                "verify_rules": ["not_a_real_rule"],
                "delta_mode": "none",
                "strict_change_default": False,
            },
            "architecture": {
                "artifacts": ["proposal", "design", "tasks"],
                "delta_mode": "none",
                "strict_change_default": False,
            },
            "flow": {
                "artifacts": ["proposal", "design", "tasks"],
                "delta_mode": "none",
                "strict_change_default": False,
            },
            "criteria": {
                "artifacts": ["proposal", "design", "tasks"],
                "delta_mode": "none",
                "strict_change_default": False,
            },
            "decision": {
                "artifacts": ["proposal", "design", "tasks"],
                "delta_mode": "none",
                "strict_change_default": False,
            },
            "restructure": {
                "artifacts": ["proposal", "design", "tasks"],
                "delta_mode": "none",
                "strict_change_default": False,
            },
            "stack": {
                "artifacts": ["proposal", "design", "tasks"],
                "delta_mode": "none",
                "strict_change_default": False,
            },
        },
        "profiles": {
            "core": {"active": ["propose", "apply", "archive"]},
            "expanded": {"active": ["propose", "apply", "archive"]},
        },
        "tasks_template": "file:\nids:\n",
    }
    with pytest.raises(ValidationError):
        parse_workflows_dict(raw)
