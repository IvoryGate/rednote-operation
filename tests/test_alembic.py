"""Alembic migration smoke tests."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from src.core.config import DatabaseConfig, config


def test_alembic_upgrade_head_creates_orm_tables(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "mig.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setattr(config, "database", DatabaseConfig(url=url, echo=False))

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    expected = {
        "accounts",
        "notes",
        "competitors",
        "keywords",
        "content_calendar",
        "publish_queue",
        "analysis_reports",
        "knowledge_entries",
        "operation_logs",
        "alembic_version",
    }
    assert expected.issubset(tables)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert version == "0c24fffa216a"
