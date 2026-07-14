#!/usr/bin/env bash
set -euo pipefail

echo "=== RedNote Operation — Setup ==="

# Install Python dependencies
uv sync

# Install Playwright browsers (Chromium only)
uv run playwright install chromium

# Create data directories
mkdir -p data logs exports .browser-data

# Initialize database (imports ORM models before create_all)
uv run python -c "from src.core.db import init_db; init_db()"

echo ""
echo "Setup complete! Quick start:"
echo "  uv run python -m scripts.crawl.login login        # Login to Xiaohongshu"
echo "  uv run python main.py                              # Start BI dashboard"
echo ""
