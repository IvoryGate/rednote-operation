"""Tests for workflow runner and FastAPI workflow endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.db import init_db
from src.core.workflows import WorkflowRunner, WORKFLOWS, _build_analyze_performance


def test_build_analyze_performance_cmd(tmp_path: Path) -> None:
    out = tmp_path / "perf.md"
    cmd = _build_analyze_performance({"days": 7, "top": 5, "output": str(out)})
    assert "scripts/analyze/content_performance.py" in cmd
    assert "--from-db" in cmd
    assert "--days" in cmd and "7" in cmd
    assert str(out) in cmd


def test_unknown_workflow_raises() -> None:
    runner = WorkflowRunner()
    with pytest.raises(KeyError):
        runner.submit("no.such.workflow", {}, background=False)


def test_create_brief_requires_params() -> None:
    runner = WorkflowRunner()
    with pytest.raises(ValueError, match="topic and category"):
        runner.submit("create.brief", {}, background=False)


def test_sync_echo_style_job_via_python_c(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # Replace analyze.performance builder with a harmless python one-liner.
    def _echo(params: dict) -> list[str]:  # type: ignore[type-arg]
        out = Path(params["output"])
        return [
            "python",
            "-c",
            f"from pathlib import Path; Path({str(out)!r}).write_text('ok')",
        ]

    monkeypatch.setitem(
        WORKFLOWS,
        "analyze.performance",
        WORKFLOWS["analyze.performance"].__class__(
            name="analyze.performance",
            description="test",
            build_cmd=_echo,
        ),
    )
    out = tmp_path / "out.md"
    runner = WorkflowRunner(timeout_seconds=30)
    job = runner.submit(
        "analyze.performance",
        {"output": str(out)},
        background=False,
    )
    assert job.status == "succeeded"
    assert out.read_text() == "ok"


def test_workflow_api_list_and_run(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    db_file = tmp_path / "api.db"
    engine = create_engine(f"sqlite:///{db_file}")
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("src.core.db.engine", engine)
    monkeypatch.setattr("src.core.db.SessionLocal", session_factory)
    monkeypatch.setattr("main.SessionLocal", session_factory)
    init_db()

    def _echo(params: dict) -> list[str]:  # type: ignore[type-arg]
        return ["python", "-c", "print('workflow-ok')"]

    monkeypatch.setitem(
        WORKFLOWS,
        "analyze.keywords",
        WORKFLOWS["analyze.keywords"].__class__(
            name="analyze.keywords",
            description="test",
            build_cmd=_echo,
        ),
    )

    # Use a fresh runner on the app module
    from src.core import workflows as wf

    test_runner = WorkflowRunner(timeout_seconds=30)
    monkeypatch.setattr(wf, "runner", test_runner)
    monkeypatch.setattr("main.runner", test_runner)

    from main import app

    client = TestClient(app)
    listed = client.get("/api/workflows")
    assert listed.status_code == 200
    names = {w["name"] for w in listed.json()}
    assert "analyze.performance" in names

    res = client.post(
        "/api/workflows/analyze.keywords/run",
        json={"params": {}, "background": False},
    )
    assert res.status_code == 200
    job = res.json()
    assert job["status"] == "succeeded"
    assert "workflow-ok" in job["stdout"]

    got = client.get(f"/api/workflows/jobs/{job['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == job["id"]

    jobs = client.get("/api/workflows/jobs")
    assert jobs.status_code == 200
    assert any(j["id"] == job["id"] for j in jobs.json())


def test_workflow_api_not_found() -> None:
    from main import app

    client = TestClient(app)
    res = client.post("/api/workflows/does.not.exist/run", json={"params": {}})
    assert res.status_code == 404
