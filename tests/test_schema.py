"""Ensure schema.sql stays in sync with SQLAlchemy ORM models."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

import src.models  # noqa: F401  # register tables
from src.core.db import Base, init_db

SCHEMA_PATH = Path("database/schema.sql")

# Tables defined in both ORM and schema.sql
EXPECTED_TABLES = {
    "accounts",
    "notes",
    "competitors",
    "keywords",
    "content_calendar",
    "publish_queue",
    "analysis_reports",
    "knowledge_entries",
    "operation_logs",
}


def _orm_columns(table: str) -> set[str]:
    return {col.name for col in Base.metadata.tables[table].columns}


def _sql_columns(table: str) -> set[str]:
    sql = SCHEMA_PATH.read_text()
    # Extract CREATE TABLE body for the given table
    pattern = rf"CREATE TABLE IF NOT EXISTS {table}\s*\((.*?)\);"
    match = re.search(pattern, sql, re.DOTALL | re.IGNORECASE)
    assert match, f"table {table} missing from schema.sql"
    body = match.group(1)
    cols: set[str] = set()
    for line in body.splitlines():
        line = line.strip().rstrip(",")
        if not line or line.upper().startswith("PRIMARY KEY") or line.upper().startswith("UNIQUE"):
            continue
        # first token is column name
        col = line.split()[0]
        cols.add(col)
    return cols


def test_schema_sql_exists() -> None:
    assert SCHEMA_PATH.exists()


def test_orm_and_schema_table_names_match() -> None:
    orm_tables = set(Base.metadata.tables.keys())
    assert orm_tables == EXPECTED_TABLES


def test_orm_and_schema_columns_match() -> None:
    for table in sorted(EXPECTED_TABLES):
        orm_cols = _orm_columns(table)
        sql_cols = _sql_columns(table)
        assert orm_cols == sql_cols, (
            f"{table}: ORM-only={orm_cols - sql_cols}, schema-only={sql_cols - orm_cols}"
        )


def test_init_db_creates_all_tables(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    monkeypatch.setattr("src.core.db.engine", engine)
    monkeypatch.setattr("src.core.db.SessionLocal", sessionmaker(bind=engine))

    init_db()

    inspector = inspect(engine)
    created = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(created)


def test_schema_sql_creates_all_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "schema.db"
    conn = sqlite3.connect(db_file)
    try:
        conn.executescript(SCHEMA_PATH.read_text())
        conn.commit()
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert EXPECTED_TABLES.issubset(tables)
    finally:
        conn.close()
