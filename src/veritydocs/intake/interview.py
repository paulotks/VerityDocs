from __future__ import annotations

QUESTIONS = [
    ("descricao", "Pode descrever em uma frase o que o sistema deve fazer?"),
    ("contexto", "Qual o problema real que isso resolve?"),
    ("ator", "Quem e a pessoa afetada ou que dispara essa acao?"),
    ("regra", "Qual o comportamento esperado do sistema?"),
    ("edge_cases", "Existe alguma condicao de excecao ou caso especial?"),
    ("criterio_aceite", "Como saberemos que esta funcionando corretamente?"),
    ("escopo", "Isso e para o MVP ou para fase 2?"),
    ("restricoes", "Existe alguma restricao tecnica ou de seguranca?"),
]

REQUIRED = {"descricao", "ator", "regra", "criterio_aceite", "escopo"}


def is_complete(fields: dict[str, object]) -> bool:
    return REQUIRED.issubset({k for k, v in fields.items() if str(v).strip()})
