# RedNote Operation — AI Agent Guide

## Project Overview

AI-driven Xiaohongshu (小红书) operation system with modules for competitive research,
data analysis, content creation, and auto publishing.

## Architecture

```
rednote-operation/
├── src/core/          Python core engine (browser, db, config, utils)
├── scripts/           CLI scripts — the system's "hands"
│   ├── crawl/         Data collection
│   ├── analyze/       Data analysis
│   ├── create/        Content creation
│   └── publish/       Auto publishing
├── knowledge/         Domain knowledge base (rules, templates, prompts)
├── skills/            AI agent skill definitions (SKILL.md)
├── database/          Schema & migrations
├── config/            YAML configuration
├── frontend/          Vue 3 BI dashboard (read-only data visualization)
├── AGENTS.md          ← You are here
└── .cursorrules       Cursor working rules
```

## Orchestrator Workflow

The orchestrator agent follows this exact sequence for each task:

```
1. git checkout main && git pull
2. Read TODO from todowrite or AGENTS.md
3. git checkout -b <type>/<scope>-<short-description>
4. Implement or delegate work on the branch
5. pre-commit run --all-files          # Must pass
6. git add . && git commit             # Conventional Commits
7. git push origin <branch-name>       # Push to GitHub
8. Create GitHub PR                    # Target: main
9. Ensure PR checks pass (pre-commit, tests)
10. Merge PR — use ordinary merge (not squash/rebase)
11. git checkout main && git pull
12. git branch -d <branch-name>        # Clean up local
13. Update TODO status
```

## Branch Rules

| Element | Rule |
|---------|------|
| Base | Always `main`, always pull latest first |
| Name | `<type>/<scope>-<description>` |
| Types | `feat`, `fix`, `docs`, `refactor`, `chore`, `test` |
| Scopes | `core`, `scripts`, `crawl`, `analyze`, `create`, `publish`, `web`, `browser`, `db`, `config`, `deps`, `knowledge`, `skills` |
| Scope | Exactly one concern per branch |
| Size | Max 10 file changes |
| History | Multiple commits allowed, no squash on merge |

## Commit Rules

```
<type>(<scope>): <imperative-description>
```

Valid types: `feat`, `fix`, `docs`, `refactor`, `chore`, `test`

Examples:
- `feat(crawl): add note collection script with keyword filter`
- `fix(browser): handle login session expiration`
- `feat(knowledge): add food category post templates`
- `docs(agents): update orchestrator workflow`

The commit-msg hook (via commitizen) enforces this format. Non-compliant commits
are rejected automatically.

## Directory Roles

| Directory | AI Agent's Relationship |
|-----------|------------------------|
| `scripts/` | Execute via `uv run python scripts/xxx.py`. Each script is self-contained with `--help`. |
| `src/core/` | Import as `from src.core.xxx import Xxx`. Core engine, not directly executed. |
| `knowledge/` | Read for context before generation. Write to `learnings/` after key insights. |
| `skills/` | Read SKILL.md files to understand how to execute multi-step tasks. |
| `config/` | Read config.yaml for settings. accounts.yaml is gitignored (local secrets). |
| `frontend/` | Vue 3 BI dashboard. Read-only data visualization. Use npm/nuxi commands. |

## Pre-commit Verification

Before every commit, the orchestrator MUST ensure:

- [ ] `pre-commit run --all-files` passes (lint, format, type check, YAML/TOML validation)
- [ ] Commit message matches Conventional Commits format
- [ ] No debug code, print statements, or TODO comments left in
- [ ] No secrets/tokens committed (detect-private-key hook blocks this)

## Pre-push Verification

When pushing to `main`, the pre-push hook runs automatically:

- [ ] Full test suite passes
- [ ] Database schema is valid

## Merge Checklist

Before merging a PR to main, the orchestrator verifies:

- [ ] Branch is up to date with latest `main`
- [ ] All pre-commit checks passed
- [ ] All commits follow Conventional Commits
- [ ] All tests pass
- [ ] No unintended changes (review diff)
- [ ] Max 10 files changed
- [ ] knowledge/learnings updated if applicable

## Quick Reference

```bash
uv sync                    # Install dependencies
uv add <package>           # Add runtime dependency
uv add --dev <package>     # Add dev dependency
uv run python script.py    # Run script in venv
pre-commit run --all-files # Run all checks
uv run pytest              # Run tests
```

## Model Providers

This project does NOT directly call LLM APIs in scripts. Scripts process structured
data and produce structured output. The AI agent (Cursor/Codex) uses its own model
to make decisions, generate content, and interpret results.
