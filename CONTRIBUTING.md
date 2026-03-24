# Contributing

## Setup local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quality gates

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/veritydocs/
pytest --cov=veritydocs --cov-report=term-missing
```

## Padroes

- Python 3.11+
- Ruff para lint/format
- MyPy em modo estrito
- Testes em `tests/` usando `pytest`

## Pull requests

1. Abra branch com descricao clara da mudanca
2. Execute quality gates localmente
3. Inclua testes para comportamento novo ou corrigido
4. Abra PR descrevendo contexto, mudancas e plano de testes
