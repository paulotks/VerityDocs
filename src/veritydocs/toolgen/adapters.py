from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from veritydocs import __version__
from veritydocs.toolgen.canonical_render import (
    CANONICAL_SKILL_IDS,
    CANONICAL_WORKFLOW_IDS,
    render_skill_body,
    render_workflow_body,
)
from veritydocs.toolgen.context import GeneratedFile, GenerationContext


def _lang_en(ctx: GenerationContext) -> bool:
    return ctx.language == "en"


def _skill_frontmatter(name: str, description: str) -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n"


@runtime_checkable
class ToolAdapter(Protocol):
    """Contrato para artefatos por ferramenta de agente (MVP: Cursor, Claude)."""

    tool_id: str
    display_name: str
    detect_paths: Sequence[str]

    def detect_existing(self, project_dir: Path) -> bool:
        """True se o projeto já contém marcas desta ferramenta."""

    def generate_rules(self, ctx: GenerationContext) -> list[GeneratedFile]:
        ...

    def generate_workflows(self, ctx: GenerationContext) -> list[GeneratedFile]:
        ...

    def generate_skills(self, ctx: GenerationContext) -> list[GeneratedFile]:
        ...

    def generate_mcp_config(self, ctx: GenerationContext) -> list[GeneratedFile]:
        ...


class CursorAdapter:
    tool_id: str = "cursor"
    display_name: str = "Cursor"
    detect_paths: Sequence[str] = (".cursor", ".cursorrules")

    def detect_existing(self, project_dir: Path) -> bool:
        return any((project_dir / rel).exists() for rel in self.detect_paths)

    def generate_rules(self, ctx: GenerationContext) -> list[GeneratedFile]:
        en = _lang_en(ctx)
        core = (
            "---\n"
            'description: "VerityDocs: operate only from documented context"\n'
            'globs: ["docs/**/*.md"]\n'
            "alwaysApply: false\n"
            "---\n\n"
        )
        if en:
            body = (
                "## VerityDocs — documented context only\n\n"
                "- Use only facts present under `docs/` (PRD, SPEC, flows, changes, audit).\n"
                "- If information is missing, say so and suggest `vrtdocs:propose` or intake.\n"
                "- Keep identifiers `REQ-*` and `DEC-*` consistent when editing.\n"
            )
        else:
            body = (
                "## VerityDocs — apenas contexto documentado\n\n"
                "- Use apenas factos presentes em `docs/` (PRD, SPEC, flows, changes, audit).\n"
                "- Se faltar informacao, diga-o e sugira `vrtdocs:propose` ou intake.\n"
                "- Mantenha identificadores `REQ-*` e `DEC-*` consistentes ao editar.\n"
            )

        bullets_en = [
            "- **vrtdocs:propose** — new change under `docs/changes/<slug>/` (4 core files).",
            "- **vrtdocs:explore** — map existing docs; optional summary; hand off to propose.",
            "- **vrtdocs:apply** — run `tasks.md`; then `veritydocs trace` + `veritydocs check`.",
            "- **vrtdocs:archive** — applied change → `docs/changes/archive/YYYY-MM-DD-<name>/`.",
            "- **vrtdocs:verify** — strict check, trace, audit; write verification report.",
            "- **vrtdocs:sync** — run `veritydocs sync`; refresh generated rules/skills.",
            "- **vrtdocs:onboard** — explain `docs/` layout and the workflow catalogue.",
            "- **vrtdocs:lang** — update language in config + sync; no silent bulk translation.",
        ]
        bullets_pt = [
            "- **vrtdocs:propose** — novo change em `docs/changes/<slug>/` (4 ficheiros nucleo).",
            "- **vrtdocs:explore** — mapear docs existentes; resumo opcional; passar a propose.",
            "- **vrtdocs:apply** — `tasks.md`; depois `veritydocs trace` + `veritydocs check`.",
            "- **vrtdocs:archive** — aplicado → `docs/changes/archive/AAAA-MM-DD-<nome>/`.",
            "- **vrtdocs:verify** — check estrito, trace, auditoria; relatorio de verificacao.",
            "- **vrtdocs:sync** — `veritydocs sync`; refrescar rules/skills gerados.",
            "- **vrtdocs:onboard** — explicar layout de `docs/` e o catalogo de workflows.",
            "- **vrtdocs:lang** — idioma na config + sync; sem traducao em massa silenciosa.",
        ]
        if en:
            wf = (
                "---\n"
                'description: "VerityDocs conversational workflows (vrtdocs:*)"\n'
                'globs: ["docs/**/*.md", "veritydocs/**/*.yaml"]\n'
                "alwaysApply: false\n"
                "---\n\n"
                "## Workflows\n\n"
                "Drive documentation changes with agent workflows; full steps in "
                "`.cursor/commands/vrtdocs-*.md`:\n\n"
                + "\n".join(bullets_en)
                + "\n\n"
                + "CLI config: `veritydocs.config.yaml` (or legacy `VerityDocs.config.json`). "
                "Workflow catalogue: `veritydocs/workflows.yaml`.\n"
            )
        else:
            wf = (
                "---\n"
                'description: "VerityDocs — workflows conversacionais (vrtdocs:*)"\n'
                'globs: ["docs/**/*.md", "veritydocs/**/*.yaml"]\n'
                "alwaysApply: false\n"
                "---\n\n"
                "## Workflows\n\n"
                "Mudancas documentais via agente; passos completos em "
                "`.cursor/commands/vrtdocs-*.md`:\n\n"
                + "\n".join(bullets_pt)
                + "\n\n"
                + "Config CLI: `veritydocs.config.yaml` (ou legado `VerityDocs.config.json`). "
                "Catalogo: `veritydocs/workflows.yaml`.\n"
            )

        return [
            GeneratedFile(Path(".cursor") / "rules" / "veritydocs-core.mdc", core + body),
            GeneratedFile(Path(".cursor") / "rules" / "veritydocs-workflows.mdc", wf),
        ]

    def generate_workflows(self, ctx: GenerationContext) -> list[GeneratedFile]:
        en = _lang_en(ctx)
        titles_en: dict[str, str] = {
            "propose": "propose a documentation change",
            "explore": "explore a topic against existing docs",
            "apply": "apply an open documentation change",
            "archive": "archive a completed documentation change",
            "verify": "run full documentation verification",
            "sync": "regenerate agent artifacts from config",
            "onboard": "onboard to VerityDocs layout and workflows",
            "lang": "switch project language for VerityDocs",
        }
        titles_pt: dict[str, str] = {
            "propose": "propor mudanca documental",
            "explore": "explorar um topico face aos docs existentes",
            "apply": "aplicar change documental aberto",
            "archive": "arquivar change documental concluido",
            "verify": "executar verificacao documental completa",
            "sync": "regenerar artefactos do agente a partir da config",
            "onboard": "integrar no layout VerityDocs e workflows",
            "lang": "mudar idioma do projecto no VerityDocs",
        }
        titles = titles_en if en else titles_pt
        out: list[GeneratedFile] = []
        for wid in CANONICAL_WORKFLOW_IDS:
            fname = f"vrtdocs-{wid}.md"
            title = titles[wid]
            body = render_workflow_body(wid, ctx)
            header = f'---\ndescription: "VerityDocs — {title}"\n---\n\n'
            out.append(
                GeneratedFile(Path(".cursor") / "commands" / fname, header + body + "\n"),
            )
        return out

    def generate_skills(self, ctx: GenerationContext) -> list[GeneratedFile]:
        return []

    def generate_mcp_config(self, ctx: GenerationContext) -> list[GeneratedFile]:
        mcp = {
            "mcpServers": {
                "context7": {
                    "command": "npx",
                    "args": ["-y", "@upstash/context7-mcp@latest"],
                }
            }
        }
        return [
            GeneratedFile(
                Path(".cursor") / "mcp.json",
                json.dumps(mcp, indent=2),
            ),
        ]


class ClaudeAdapter:
    tool_id: str = "claude"
    display_name: str = "Claude (Claude Code / CLAUDE.md)"
    detect_paths: Sequence[str] = (".claude", "CLAUDE.md")

    def detect_existing(self, project_dir: Path) -> bool:
        return any((project_dir / rel).exists() for rel in self.detect_paths)

    @staticmethod
    def _skill_descriptions() -> dict[str, tuple[str, str]]:
        """skill_stem -> (description_en, description_pt)"""
        return {
            "context-only-docs": (
                "Operate only from documented context",
                "Operar apenas com contexto documentado",
            ),
            "docs-audit-consistency": (
                "PRD-SPEC audit and consistency",
                "Auditoria e consistencia PRD-SPEC",
            ),
            "mermaid-flows": (
                "Mermaid flows aligned with requirements",
                "Fluxos Mermaid alinhados a requisitos",
            ),
            "traceability-update": (
                "Keep traceability matrix current",
                "Manter matriz de rastreabilidade actualizada",
            ),
            "decision-capture": (
                "Capture architecture and technical decisions",
                "Capturar decisoes de arquitetura e tecnicas",
            ),
            "skill-evolution": (
                "Evolve agent skills when stack or patterns change",
                "Evoluir skills do agente quando o stack ou padroes mudam",
            ),
        }

    def generate_rules(self, ctx: GenerationContext) -> list[GeneratedFile]:
        marker_start = "<!-- veritydocs:start -->"
        marker_end = "<!-- veritydocs:end -->"
        en = _lang_en(ctx)
        if en:
            block = (
                f"{marker_start}\n"
                f"## VerityDocs ({__version__})\n\n"
                f"Project **{ctx.project_name}** — documentation workflows `vrtdocs:*`. "
                "Skills live in `.claude/skills/veritydocs-*.md`. "
                "Config: `veritydocs.config.yaml`. Catalogue: `veritydocs/workflows.yaml`.\n"
                f"{marker_end}\n"
            )
        else:
            block = (
                f"{marker_start}\n"
                f"## VerityDocs ({__version__})\n\n"
                f"Projeto **{ctx.project_name}** — workflows documentais `vrtdocs:*`. "
                "Skills em `.claude/skills/veritydocs-*.md`. "
                "Config: `veritydocs.config.yaml`. Catalogo: `veritydocs/workflows.yaml`.\n"
                f"{marker_end}\n"
            )

        root = ctx.project_dir
        claude_md = root / "CLAUDE.md"
        if claude_md.exists():
            text = claude_md.read_text(encoding="utf-8")
            if marker_start in text and marker_end in text:
                before, rest = text.split(marker_start, 1)
                _, after = rest.split(marker_end, 1)
                new_text = before + block + after
            else:
                new_text = text.rstrip() + "\n\n" + block
        else:
            new_text = f"# {ctx.project_name}\n\n" + block

        return [GeneratedFile(Path("CLAUDE.md"), new_text)]

    def generate_workflows(self, ctx: GenerationContext) -> list[GeneratedFile]:
        return []

    def generate_skills(self, ctx: GenerationContext) -> list[GeneratedFile]:
        en = _lang_en(ctx)
        desc_map = self._skill_descriptions()
        out: list[GeneratedFile] = []
        for stem in CANONICAL_SKILL_IDS:
            de, dp = desc_map[stem]
            desc = de if en else dp
            sid = f"veritydocs-{stem}"
            fname = f"{sid}.md"
            body = render_skill_body(stem, ctx)
            content = _skill_frontmatter(sid, desc) + body + "\n"
            out.append(GeneratedFile(Path(".claude") / "skills" / fname, content))
        return out

    def generate_mcp_config(self, ctx: GenerationContext) -> list[GeneratedFile]:
        return []
