# RedNote Operation

AI-driven Xiaohongshu (小红书) operation system with modules for competitive research,
data analysis, content creation, and auto publishing.

## Architecture

```
├── scripts/     CLI scripts — the system's "hands"
├── src/core/    Python core engine (browser, db, config)
├── knowledge/   Domain knowledge base
├── skills/      AI agent skill definitions (SKILL.md)
├── database/    Schema & migrations
├── config/      Configuration files
└── frontend/    Vue 3 BI dashboard (read-only)
```

## Quick Start

```bash
uv sync                     # Install dependencies
uv run playwright install   # Install browser engine
uv run python main.py       # Start the API server
```

## Development

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
uv run pre-commit run --all-files
uv run pytest
```

## Git Workflow

This project follows Conventional Commits and a strict branch workflow.
See [AGENTS.md](AGENTS.md) for details.
