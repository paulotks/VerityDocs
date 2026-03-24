"""Tests for scaffold tool selection aligned with registered adapters."""

from __future__ import annotations

import pytest

from veritydocs.scaffold.tool_selector import parse_and_validate_tools_csv
from veritydocs.toolgen.registry import list_adapter_ids


def test_parse_tools_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="sem adaptador"):
        parse_and_validate_tools_csv("cursor,gemini")


def test_parse_tools_rejects_empty_effective_list() -> None:
    with pytest.raises(ValueError, match="pelo menos uma ferramenta"):
        parse_and_validate_tools_csv("   ,  ,  ")


def test_parse_tools_accepts_registered_and_dedupes() -> None:
    out = parse_and_validate_tools_csv("claude,cursor,claude")
    assert out == ["claude", "cursor"]


def test_parse_tools_lists_supported_ids_in_error() -> None:
    with pytest.raises(ValueError) as excinfo:
        parse_and_validate_tools_csv("nope")
    msg = str(excinfo.value)
    for tid in list_adapter_ids():
        assert tid in msg
