# {{ project_name }}

Projeto criado com VerityDocs no dominio `{{ domain }}`.

## Visao
- Linguagem de documentacao: `{{ language }}`
- Estrutura pronta para PRD, SPEC, flows, changes e audit

## Proximos passos
1. Preencher os ficheiros em `docs/PRD/` e `docs/SPEC/` (indices em `_index.md`)
2. Configurar workflows em `veritydocs/workflows.yaml` se necessario
3. Rodar `veritydocs trace` e `veritydocs check --strict` (config: `veritydocs.config.yaml`)
