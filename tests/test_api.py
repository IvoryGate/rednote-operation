"""Smoke tests for FastAPI read-only endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.db import init_db
from src.models import Competitor, Keyword, Note, PublishQueue


@pytest.fixture()
def client(tmp_path: Path, monkeypatch) -> TestClient:  # type: ignore[no-untyped-def]
    db_file = tmp_path / "api.db"
    engine = create_engine(f"sqlite:///{db_file}")
    session_factory = sessionmaker(bind=engine)

    monkeypatch.setattr("src.core.db.engine", engine)
    monkeypatch.setattr("src.core.db.SessionLocal", session_factory)
    monkeypatch.setattr("main.SessionLocal", session_factory)

    init_db()

    # Seed minimal data
    db = session_factory()
    try:
        db.add(
            Note(
                note_id="n1",
                title="Test Note",
                like_count=10,
                collect_count=2,
                comment_count=1,
                share_count=0,
            )
        )
        db.add(
            Competitor(
                account_id=1,
                competitor_name="竞品A",
                followers=1000,
                notes_count=50,
                avg_likes=100.0,
                is_active=True,
            )
        )
        db.add(Keyword(keyword="美食探店", search_volume=500, competition=0.3, is_active=True))
        db.add(
            PublishQueue(
                account_id=1,
                title="待发布标题",
                status="pending",
            )
        )
        db.commit()
    finally:
        db.close()

    from main import app

    return TestClient(app)


def test_dashboard_stats(client: TestClient) -> None:
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_notes"] == 1
    assert data["total_likes"] == 10
    assert data["total_followers"] == 1000
    assert "daily_stats" in data


def test_list_competitors(client: TestClient) -> None:
    res = client.get("/api/competitors")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["competitor_name"] == "竞品A"


def test_list_notes(client: TestClient) -> None:
    res = client.get("/api/notes")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Note"


def test_list_keywords(client: TestClient) -> None:
    res = client.get("/api/keywords")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["keyword"] == "美食探店"


def test_queue_list(client: TestClient) -> None:
    res = client.get("/api/queue?status=pending")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["title"] == "待发布标题"


def test_config_loads_yaml() -> None:
    from src.core.config import Config

    cfg = Config.from_yaml("config/config.yaml")
    assert cfg.app.name == "RedNote Operation"
    assert cfg.database.url.startswith("sqlite:///")
    assert cfg.schedule.timezone == "Asia/Shanghai"
