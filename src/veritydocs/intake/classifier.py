from __future__ import annotations


def classify_requirement(text: str) -> str:
    lowered = text.lower()
    if any(k in lowered for k in ["segur", "latencia", "performance", "sla"]):
        return "NFR"
    if any(k in lowered for k in ["aceite", "criterio", "teste"]):
        return "ACE"
    if any(k in lowered for k in ["perfil", "permiss", "acesso", "rbac"]):
        return "RBAC"
    if any(k in lowered for k in ["jornada", "fluxo", "etapa"]):
        return "JOR"
    return "FUNC"
