from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from veritydocs.toolgen.adapters import ToolAdapter
from veritydocs.toolgen.registry import get_adapter, list_adapter_ids


def _adapters_in_registry_order() -> tuple[ToolAdapter, ...]:
    out: list[ToolAdapter] = []
    for tid in list_adapter_ids():
        ad = get_adapter(tid)
        if ad is not None:
            out.append(ad)
    return tuple(out)


def _default_tool_id() -> str:
    ids = list_adapter_ids()
    if not ids:
        return "cursor"
    return ids[0]


def parse_and_validate_tools_csv(csv: str) -> list[str]:
    """
    Interpreta ``--tools`` (lista separada por vírgulas).
    Rejeita ids sem adaptador registado ou lista vazia após normalização.

    Raises:
        ValueError: ferramentas desconhecidas ou nenhum id válido.
    """
    valid = frozenset(list_adapter_ids())
    raw = [p.strip().lower() for p in csv.split(",") if p.strip()]
    if not raw:
        msg = "Indique pelo menos uma ferramenta em --tools (ex.: cursor,claude)."
        raise ValueError(msg)
    unknown = [tid for tid in raw if tid not in valid]
    if unknown:
        supported = ", ".join(list_adapter_ids())
        uniq = ", ".join(dict.fromkeys(unknown))
        msg = f"Ferramenta(s) sem adaptador: {uniq}. Suportadas nesta versao: {supported}."
        raise ValueError(msg)
    seen: set[str] = set()
    out: list[str] = []
    for tid in raw:
        if tid not in seen:
            seen.add(tid)
            out.append(tid)
    return out


def select_tools(project_dir: Path, tools_csv: str | None) -> list[str]:
    """
    Resolve a lista de ferramentas: CSV em --tools, ou deteccao + prompt interativo,
    ou deteccao/default em ambiente nao interativo.
    """
    if tools_csv is not None and tools_csv.strip():
        return parse_and_validate_tools_csv(tools_csv)

    adapters = _adapters_in_registry_order()
    fallback = _default_tool_id()
    if not adapters:
        return [fallback]

    detected = [a.tool_id for a in adapters if a.detect_existing(project_dir)]

    if not sys.stdin.isatty():
        return detected or [fallback]

    console = Console()
    if detected:
        console.print("[cyan]Ferramentas detetadas no diretorio:[/cyan] " + ", ".join(detected))
    chosen = list(detected)
    for adapter in adapters:
        if adapter.tool_id in chosen:
            continue
        if Confirm.ask(f"Incluir artefatos para {adapter.display_name}?", default=False):
            chosen.append(adapter.tool_id)
    if not chosen and Confirm.ask(
        f"Incluir {adapters[0].display_name} (recomendado para MVP)?",
        default=True,
    ):
        chosen.append(adapters[0].tool_id)
    return chosen or [fallback]
