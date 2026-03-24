from __future__ import annotations

from veritydocs.toolgen.adapters import ClaudeAdapter, CursorAdapter, ToolAdapter

_BUILTIN: list[ToolAdapter] = [
    CursorAdapter(),
    ClaudeAdapter(),
]

_ADAPTERS: dict[str, ToolAdapter] = {a.tool_id: a for a in _BUILTIN}


def get_adapter(tool_id: str) -> ToolAdapter | None:
    """Resolve adaptador pelo id canónico (ex.: ``cursor``, ``claude``)."""
    return _ADAPTERS.get(tool_id.strip().lower())


def list_adapter_ids() -> tuple[str, ...]:
    """Ids registados, ordenados."""
    return tuple(sorted(_ADAPTERS))


def register_adapter(adapter: ToolAdapter, *, override: bool = False) -> None:
    """
    Regista ou substitui um adaptador (extensões e testes).

    Raises:
        ValueError: se ``override`` for False e o id já existir.
    """
    tid = adapter.tool_id
    if tid in _ADAPTERS and not override:
        msg = f"Adaptador já registado para '{tid}'; use override=True para substituir."
        raise ValueError(msg)
    _ADAPTERS[tid] = adapter


def adapters_snapshot() -> dict[str, ToolAdapter]:
    """Cópia superficial do registo (útil para inspeção)."""
    return dict(_ADAPTERS)
