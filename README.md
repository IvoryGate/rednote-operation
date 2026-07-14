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
uv sync                     # Install package + dependencies (editable)
uv run playwright install   # Install browser engine
uv run alembic upgrade head # Apply database migrations
uv run python main.py       # Start the API server
uv run python scripts/crawl/login.py --help   # CLI scripts work without PYTHONPATH
```

### Existing database (created before Alembic)

If `database/rednote.db` already exists from `create_all` / older setup:

```bash
uv run alembic stamp head   # mark current schema as baseline without recreating tables
```

Only run `upgrade head` on empty DBs or after reviewing new revisions.
New schema changes: `uv run alembic revision --autogenerate -m "..." && uv run alembic upgrade head`.

### Publish selector smoke

```bash
uv run python scripts/publish/smoke_selectors.py           # offline YAML/registry check
uv run python scripts/publish/smoke_selectors.py --live    # needs login session
```

CI runs the offline check after pytest on every PR / push to `main`.

### Workflow API auth

`POST /api/workflows/{name}/run` accepts `Authorization: Bearer <token>` or `X-API-Token`.

```bash
# config/config.yaml → security.api_token, or:
export REDNOTE_API_TOKEN=your-secret
```

When the effective token is non-empty (or `security.require_token: true`), the run endpoint
requires it. Real `publish.now` (`dry_run=false`) also needs
`confirm_publish: "I_CONFIRM_PUBLISH"`; otherwise the runner forces dry-run.

## Development

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
uv run pre-commit run --all-files
uv run pytest
```

## Git Workflow

This project follows Conventional Commits and a strict branch workflow.
See [AGENTS.md](AGENTS.md) for details.
