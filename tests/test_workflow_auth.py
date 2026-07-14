"""Tests for workflow API token auth and publish confirm guard."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.db import init_db
from src.core.workflow_auth import (
    PUBLISH_CONFIRM_PHRASE,
    auth_required,
    effective_api_token,
    extract_token_from_headers,
    guard_workflow_params,
    verify_bearer_token,
)
from src.core.workflows import WORKFLOWS, WorkflowRunner


def test_extract_token_prefers_x_api_token() -> None:
    assert (
        extract_token_from_headers("Bearer from-auth", "from-header") == "from-header"
    )
    assert extract_token_from_headers("Bearer only-auth", None) == "only-auth"
    assert extract_token_from_headers(None, None) is None


def test_verify_open_when_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDNOTE_API_TOKEN", raising=False)
    monkeypatch.delenv("REDNOTE_SECURITY__API_TOKEN", raising=False)
    monkeypatch.setattr("src.core.workflow_auth.config.security.api_token", "")
    monkeypatch.setattr("src.core.workflow_auth.config.security.require_token", False)
    assert effective_api_token() == ""
    assert auth_required() is False
    assert verify_bearer_token(None) is True


def test_verify_requires_matching_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDNOTE_API_TOKEN", "s3cret")
    monkeypatch.setattr("src.core.workflow_auth.config.security.require_token", False)
    assert auth_required() is True
    assert verify_bearer_token("s3cret") is True
    assert verify_bearer_token("wrong") is False
    assert verify_bearer_token(None) is False


def test_guard_publish_blocks_or_defaults_dry_run() -> None:
    with pytest.raises(ValueError, match="Real publish blocked"):
        guard_workflow_params("publish.now", {"dry_run": False, "queue_id": 1})
    ok = guard_workflow_params("publish.now", {"queue_id": 1})
    assert ok["dry_run"] is True


def test_guard_publish_allows_confirmed_live() -> None:
    out = guard_workflow_params(
        "publish.now",
        {
            "dry_run": False,
            "confirm_publish": PUBLISH_CONFIRM_PHRASE,
            "queue_id": 1,
        },
    )
    assert out["dry_run"] is False


def test_guard_other_workflows_passthrough() -> None:
    params = {"days": 7}
    assert guard_workflow_params("analyze.performance", params) == params


def test_submit_blocks_unconfirmed_live_publish() -> None:
    runner = WorkflowRunner()
    with pytest.raises(ValueError, match="Real publish blocked"):
        runner.submit(
            "publish.now",
            {"dry_run": False, "queue_id": 1},
            background=False,
        )


def test_workflow_api_rejects_missing_token(
    tmp_path,  # type: ignore[no-untyped-def]
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_file = tmp_path / "api.db"
    engine = create_engine(f"sqlite:///{db_file}")
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("src.core.db.engine", engine)
    monkeypatch.setattr("src.core.db.SessionLocal", session_factory)
    monkeypatch.setattr("main.SessionLocal", session_factory)
    init_db()

    monkeypatch.setenv("REDNOTE_API_TOKEN", "locked")

    def _echo(_params: dict[str, object]) -> list[str]:
        return ["python", "-c", "print('ok')"]

    monkeypatch.setitem(
        WORKFLOWS,
        "analyze.keywords",
        WORKFLOWS["analyze.keywords"].__class__(
            name="analyze.keywords",
            description="test",
            build_cmd=_echo,
        ),
    )
    from src.core import workflows as wf

    test_runner = WorkflowRunner(timeout_seconds=30)
    monkeypatch.setattr(wf, "runner", test_runner)
    monkeypatch.setattr("main.runner", test_runner)

    from main import app

    client = TestClient(app)
    denied = client.post("/api/workflows/analyze.keywords/run", json={"params": {}})
    assert denied.status_code == 401

    ok = client.post(
        "/api/workflows/analyze.keywords/run",
        json={"params": {}, "background": False},
        headers={"X-API-Token": "locked"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "succeeded"
