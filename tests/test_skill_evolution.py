"""Tests for skill-evolution stack helpers."""

from __future__ import annotations

from veritydocs.skill_evolution import (
    CONTEXT7_MCP_QUERY_DOCS_TOOL,
    CONTEXT7_MCP_RESOLVE_LIBRARY_TOOL,
    merge_stack_entries,
    normalize_stack_entry,
)


def test_normalize_stack_entry_basic() -> None:
    assert normalize_stack_entry("  NestJS  ") == "nestjs"
    assert normalize_stack_entry("PostgreSQL") == "postgresql"
    assert normalize_stack_entry("next.js") == "next.js"


def test_merge_stack_entries_order_and_dedupe() -> None:
    assert merge_stack_entries(["nestjs", "postgresql"], ["PostgreSQL", "rabbitmq"]) == [
        "nestjs",
        "postgresql",
        "rabbitmq",
    ]


def test_context7_mcp_tool_names() -> None:
    assert "resolve" in CONTEXT7_MCP_RESOLVE_LIBRARY_TOOL.lower()
    assert "query" in CONTEXT7_MCP_QUERY_DOCS_TOOL.lower()
