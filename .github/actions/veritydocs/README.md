# VerityDocs GitHub Action

Executa o comando `veritydocs check` dentro de workflows.

## Uso

```yaml
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: ./.github/actions/veritydocs
        with:
          config: VerityDocs.config.json
          strict: "true"
```
