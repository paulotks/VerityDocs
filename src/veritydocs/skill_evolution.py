"""Utilitários e contrato de referência para o meta-skill skill-evolution e Context7 MCP.

O fluxo inteligente (extracção, consultas MCP, decisões) é executado pelo agente; este
módulo oferece funções puras para normalizar o stack e nomes estáveis dos tools MCP.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Final

# Referência: servidor MCP Context7 (ex.: `@upstash/context7-mcp`). Os nomes exactos
# dos tools podem variar ligeiramente por host; no Cursor são tipicamente:
CONTEXT7_MCP_RESOLVE_LIBRARY_TOOL: Final = "mcp_context7_resolve-library-id"
CONTEXT7_MCP_QUERY_DOCS_TOOL: Final = "mcp_context7_query-docs"


def normalize_stack_entry(raw: str) -> str:
    """Normaliza um identificador de tecnologia para entrada no stack (minúsculas, hífens)."""
    s = raw.strip().lower()
    s = re.sub(r"[\s_/]+", "-", s)
    s = re.sub(r"[^a-z0-9.-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def merge_stack_entries(existing: list[str], additions: Iterable[str]) -> list[str]:
    """Junta listas mantendo ordem estável e sem duplicar (comparação por forma normalizada)."""
    seen: set[str] = set()
    out: list[str] = []
    for item in list(existing) + list(additions):
        n = normalize_stack_entry(item)
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out
