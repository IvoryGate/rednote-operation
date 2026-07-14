"""Tests for first-run preflight helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from scripts.ops.preflight import _check_accounts, main


def test_check_accounts_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    ok, status, detail = _check_accounts()
    assert ok is False
    assert status == "missing"
    assert "accounts.yaml.template" in detail


def test_check_accounts_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "accounts.yaml").write_text(
        yaml.dump({"accounts": [{"name": "main", "enabled": True}]}),
        encoding="utf-8",
    )
    ok, status, detail = _check_accounts()
    assert ok is True
    assert status == "ok"
    assert "main" in detail


def test_preflight_cli_skip_smoke_exits_on_missing_accounts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    runner = CliRunner()
    result = runner.invoke(main, ["--skip-smoke"])
    assert result.exit_code == 1
    assert "PREFLIGHT incomplete" in result.output
    assert "docs/first_run.md" in result.output
