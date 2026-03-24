# VerityDocs

Framework open source para documentação técnica modular, rastreável e auditável. A CLI expõe também um modo **CLI-as-API** (`status`, `instructions`) pensado para integração com chats de agente (Cursor, Claude Code, etc.).

## Requisitos

- Python **3.11+**

## Instalação

### Utilizador final (PyPI)

Quando o pacote estiver publicado no PyPI:

```bash
pip install veritydocs
```

O executável fica disponível como `veritydocs` (ver [`pyproject.toml`](pyproject.toml), secção `[project.scripts]`).

### A partir deste repositório (GitHub)

Instalação directa com **pip** (requer Git instalado no sistema):

```bash
pip install "git+https://github.com/paulotks/VerityDocs.git"
```

Com extras de desenvolvimento (`pytest`, `ruff`, `mypy`, etc.):

```bash
pip install "veritydocs[dev] @ git+https://github.com/paulotks/VerityDocs.git"
```

Em versões antigas do pip, pode usar: `pip install "git+https://github.com/paulotks/VerityDocs.git#egg=veritydocs[dev]"`.

Se preferir clonar e instalar em modo editável (útil para contribuir ou depurar):

```bash
git clone https://github.com/paulotks/VerityDocs.git
cd VerityDocs
pip install -e ".[dev]"
```

Repositório: [github.com/paulotks/VerityDocs](https://github.com/paulotks/VerityDocs).

### Verificar a instalação

```bash
veritydocs --version
veritydocs --help
```

---

## Guia de utilização do framework

O VerityDocs organiza documentação técnica em torno de **requisitos rastreáveis**, **mudanças documentais** (`docs/changes/<slug>/`) e **workflows** definidos em `veritydocs/workflows.yaml`. A CLI é a interface principal; os comandos `status` e `instructions` foram pensados para agentes de IA lerem o estado do projecto e seguirem passos canónicos.

### 1. Inicializar num projecto

Na raiz do repositório que quer documentar (directório do código ou monorepo):

```bash
veritydocs init --name "NomeDoProjecto" --domain api --dir . --tools cursor,claude --profile expanded
```

- **`--name`**: nome legível do projecto.
- **`--domain`**: `software`, `api`, `data-platform` ou `mobile-app`.
- **`--language` / `--lang`**: por exemplo `pt-BR` ou `en`.
- **`--profile`**: `core` (workflows mínimos) ou `expanded` (conjunto completo).
- **`--tools`**: gera artefactos para IDEs/agentes (ex.: `cursor`, `claude`); pode omitir e escolher de forma interactiva.

Isto cria `veritydocs.config.yaml`, `veritydocs/workflows.yaml`, a árvore `docs/` (PRD, SPEC, etc.) e ficheiros alinhados ao perfil escolhido.

### 2. Dia a dia: estado e roteiro

- **`veritydocs status --format md`** (ou `json`): visão agregada — configuração, changes abertos, resultado de `check`, rastreabilidade e decisões. Use **`--change <slug>`** quando houver várias pastas em `docs/changes/`.
- **`veritydocs instructions <workflow> --format md`**: instruções para o workflow pedido (`propose`, `apply`, `verify`, `sync`, etc.), com passos prefixados `vrtdocs:<id>` e sugestões `recommended_cli`.

### 3. Propor, aplicar e fechar mudanças

- Criar estrutura de mudança: `veritydocs change create <slug> --type requirement` (ou outro tipo listado em `veritydocs/workflows.yaml`).
- Depois de reflectir alterações nos documentos canónicos: `veritydocs change mark-applied <slug>` e, quando fechar o ciclo, `veritydocs change archive <slug>`.
- Requisitos em linguagem natural: `veritydocs intake` (interactivo ou `--batch` com JSON em stdin).

### 4. Qualidade e relatórios

- **`veritydocs check --strict`**: valida consistência de `docs/` e workflows.
- **`veritydocs trace --format markdown`**: matriz REQ ↔ PRD ↔ SPEC (e ficheiro `docs/traceability.md` quando aplicável).
- **`veritydocs audit [MODULE_ID]`** ou **`--all`**: auditoria por módulo ou pipeline global.
- **`veritydocs report --output docs/report.html`**: relatório HTML da matriz de rastreabilidade.
- **`veritydocs sync`**: regenera skills/regras para as ferramentas configuradas em `veritydocs.config.yaml`.

A secção [Referência de comandos](#referência-de-comandos) e a tabela [Workflows canónicos](#workflows-canónicos-veritydocs-instructions) completam este guia.

---

## Pedir à IA para instalar e integrar o VerityDocs (prompt sugerido)

Pode colar o bloco abaixo no chat do **Cursor**, **Claude**, **Copilot** ou outro assistente com acesso ao terminal e ao seu repositório. Ajuste o nome do projecto, domínio e idioma se precisar.

```text
Tarefa autónoma: integrar o framework VerityDocs no repositório actual.

1) Instalar a CLI a partir do GitHub (usa o ambiente Python do projecto ou um venv na raiz):
   pip install "git+https://github.com/paulotks/VerityDocs.git"

2) Confirmar: veritydocs --version e veritydocs --help.

3) Se ainda não existir configuração VerityDocs na raiz, executar init de forma não interactiva, por exemplo:
   veritydocs init --name "<NOME_DO_PROJECTO>" --domain software --dir . --profile expanded --tools cursor,claude
   (Ajusta --domain para api, data-platform ou mobile-app se fizer sentido; --lang pt-BR ou en conforme o projecto.)

4) Ler o README do pacote ou do repositório https://github.com/paulotks/VerityDocs para respeitar convenções; depois corre veritydocs status --format md e resume o estado ao utilizador.

5) Não commite segredos; se criares venv, adiciona-o ao .gitignore se ainda não estiver.

Executa estes passos tu próprio (comandos no terminal) e reporta o que foi criado e eventuais erros.
```

Substitua `<NOME_DO_PROJECTO>` pelo nome real. Se o assistente não tiver permissão para instalar pacotes globalmente, peça explicitamente para criar `./.venv`, activá-lo e correr `pip install` dentro desse ambiente.

---

## Configuração do projeto

Após `init`, o projeto passa a usar **`veritydocs.config.yaml`** (ou `.yml`) na raiz. O ficheiro legado **`VerityDocs.config.json`** continua suportado nos restantes comandos, se ainda existir.

Caminhos importantes (por omissão):

- Documentação: `docs/`
- Catálogo de workflows e tipos de mudança: `veritydocs/workflows.yaml`
- Mudanças documentais em curso: `docs/changes/<slug>/`

## Quickstart (linha de comandos)

```bash
veritydocs init --name MeuProjeto --domain api --dir . --tools cursor,claude --profile expanded
veritydocs trace --format markdown
veritydocs check --strict
veritydocs audit M01
veritydocs report --output docs/report.html
```

Ajuste `--domain` (`software`, `api`, `data-platform`, `mobile-app`), `--language` / `--lang` (`pt-BR`, `en`) e `--profile` (`core` | `expanded`) conforme o projeto.

---

## Fluxo sugerido de uso com chat de agente

O agente não precisa “adivinhar” o processo: use a CLI como fonte de verdade.

1. **Sincronizar contexto** — Peça ao agente (ou execute) `veritydocs status --format md` ou `--format json`. O payload inclui projeto, `workflows.active`, changes abertos, resultado de `check`, métricas de rastreabilidade, log de decisões e (se configurado) MCP Context7.

2. **Carregar o roteiro do workflow** — Para cada fase conversacional, use `veritydocs instructions <workflow> --format md` (ou `json`). O output traz `body_markdown` com passos canónicos (prefixo `vrtdocs:<id>`) e `recommended_cli` com comandos a correr em seguida.

3. **Propor mudança** — No workflow **propose**, o agente cria `docs/changes/<slug>/` com `proposal.md`, `design.md`, `tasks.md` e `metadata.yaml`, alinhado a `veritydocs/workflows.yaml`. Em alternativa pode usar `veritydocs change create <slug> --type ...` para estruturar a pasta.

4. **Aplicar e validar** — Depois de editar PRD/SPEC/flows, o agente (ou CI) corre `veritydocs check`, `veritydocs trace`, e em perfis mais exigentes `veritydocs audit`. Use `veritydocs flows generate` quando houver alterações de fluxo descritas no PRD.

5. **Fechar o ciclo** — `veritydocs change mark-applied <slug>` quando a mudança estiver refletida na documentação canónica; `veritydocs change archive <slug>` para arquivar. `veritydocs sync` regera artefactos para as ferramentas configuradas em `veritydocs.config.yaml` (skills, regras, etc.).

6. **Requisitos em linguagem natural** — `veritydocs intake` (interativo ou `--batch` via stdin JSON) classifica e guarda rascunho em `docs/changes/` (conforme `intake.draft_dir` na config).

**Dica:** combine `--change <slug>` em `status` e `instructions` para focar uma mudança concreta quando existirem várias pastas em `docs/changes/`.

---

## Referência de comandos

| Comando | Resumo |
|--------|--------|
| **`veritydocs init`** | Gera a árvore `docs/`, `veritydocs.config.yaml`, `veritydocs/workflows.yaml`, ficheiros de documento iniciais (PRD/SPEC), e artefactos para ferramentas (`--tools` ou seleção interativa). `--profile core` ou `expanded` controla workflows activos por omissão. |
| **`veritydocs status`** | Agrega estado do repositório: config, changes abertos, resultado de verificações, rastreabilidade, decisões. `--format json` \| `md`. `--change <slug>` foca um change. |
| **`veritydocs instructions <workflow>`** | Devolve instruções canónicas em Markdown ou JSON para o workflow pedido (ver tabela abaixo). Útil para colar no contexto do agente. |
| **`veritydocs sync`** | Regenera artefactos de toolgen (Cursor, Claude, etc.) conforme a config actual; exige `tools` definidos. |
| **`veritydocs trace`** | Constrói a matriz REQ ↔ PRD ↔ SPEC. `--format markdown` (por omissão escreve também `docs/traceability.md` se não houver `--output`), `json`, `csv`. |
| **`veritydocs check`** | Valida consistência do `docs/` (e `workflows.yaml`). `--strict` endurece regras; `--watch` reexecuta em ciclo; `--interval` define segundos entre ciclos; `--format text` \| `json`. |
| **`veritydocs audit [MODULE_ID]`** | Auditoria por módulo (mapeamento em `docs/audit/step0-module-mapping.json`). `--all` audita todos os módulos e corre a pipeline global (cross-module, decisões, fluxos). `--output-dir` sobrescreve o destino (config: `audit.output_dir`). |
| **`veritydocs intake`** | Entrevista guiada ou `--batch` com JSON em stdin (`description` obrigatório; outros campos opcionais). Guarda rascunho em `intake-draft.json` sob o directório configurado. |
| **`veritydocs report`** | Gera relatório HTML simples com a matriz de rastreabilidade. `--output` (por omissão `docs/report.html`). |
| **`veritydocs flows generate`** | Gera diagramas Mermaid a partir do PRD (motor `prd`). `--dry-run` não escreve ficheiros; `--format text` \| `json`. |
| **`veritydocs workflows validate`** | Valida o ficheiro `veritydocs/workflows.yaml` (tipos de mudança, artefactos, regras `verify_rules`, template de tasks). |
| **`veritydocs change create <slug>`** | Cria estrutura de mudança documental com `--type` (`requirement`, `architecture`, `flow`, `criteria`, `decision`, `restructure`, `stack`), metadados opcionais e `--skill-evolution` / `--force`. |
| **`veritydocs change mark-applied <slug>`** | Marca a mudança como aplicada (actualiza metadados). |
| **`veritydocs change archive <slug>`** | Move o change para arquivo; `--summary` e `--force` conforme necessidade. |

### Flags globais (callback principal)

- `--version` / `-V`
- `--verbose` / `-v`
- `--quiet` / `-q`
- `--no-color`

### Exemplo: intake em batch

```bash
echo "{\"description\":\"O sistema deve enviar e-mail ao concluir o pedido\",\"ator\":\"Operador\"}" | veritydocs intake --batch
```

---

## Workflows canónicos (`veritydocs instructions`)

Estes identificadores são os únicos aceites por `veritydocs instructions <id>`. Também aparecem em `default_active` / `profiles.*.active` dentro de `veritydocs/workflows.yaml` (perfil **core** vs **expanded**).

| Workflow | Resumo |
|----------|--------|
| **propose** | Transformar um pedido em linguagem natural num change estruturado sob `docs/changes/<slug>/` (proposal, design, tasks, metadata), sem inventar requisitos fora da documentação existente. |
| **explore** | Explorar o repositório de documentação e opções de desenho antes de comprometer texto canónico (útil para pesquisa e alinhamento). |
| **apply** | Aplicar o plano do change aos ficheiros canónicos (PRD, SPEC, flows, audit), mantendo referências REQ/DEC/FLOW e rastreabilidade. |
| **archive** | Encerrar e arquivar o change de forma consistente após revisão e validações. |
| **verify** | Correr validações (check, trace, audit conforme recomendado) e confirmar que o estado do repo está coerente. |
| **sync** | Alinhar artefactos gerados para IDEs/agentes com a config actual do projeto. |
| **onboard** | Orientar quem entra no projeto sobre onde está a documentação e como seguir os workflows VerityDocs. |
| **lang** | Manter consistência de idioma e convenções entre PRD, SPEC e artefactos gerados. |

---

## Tipos de mudança em `veritydocs/workflows.yaml`

O ficheiro YAML define **change_types**: cada tipo lista **artefactos** (`proposal`, `design`, `tasks`, `metadata`), **ordem** de trabalho, **verify_rules** e política **delta** / **strict_change_default**. Tipos canónicos gerados pelo `init`:

| Tipo | Resumo |
|------|--------|
| **requirement** | Mudança de requisito funcional ou de produto; delta rígido por omissão (`delta_mode: none`). |
| **architecture** | Alteração de arquitectura ou desenho; delta opcional. |
| **flow** | Mudança de jornada ou fluxo; regras extra para alinhar com `docs/flows/`. |
| **criteria** | Critérios de aceitação ou definição de “pronto”. |
| **decision** | Registo de decisão arquitectural; inclui `metadata` e regras de auditoria de decisões. |
| **restructure** | Reorganização grande da documentação; `strict_change_default: true`. |
| **stack** | Evolução de stack ou tecnologias; inclui `metadata` quando aplicável. |

Regras de verificação referenciáveis em `verify_rules` incluem, entre outras: `task_refs_required`, `trace_after_apply`, `check_after_apply`, `flows_after_flow_change`, `decisions_audit_after_decision`.

---

## Contribuição

Consulte [`CONTRIBUTING.md`](CONTRIBUTING.md) para setup local, padrões de código e processo de PR.

## Changelog

Histórico de versões em [`CHANGELOG.md`](CHANGELOG.md).
