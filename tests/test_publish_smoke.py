"""Offline publish selector smoke tests."""

from __future__ import annotations

from src.core.publish_dom import REQUIRED_CONTROLS, SelectorRegistry, offline_smoke


def test_offline_smoke_passes_on_committed_registry() -> None:
    registry = SelectorRegistry.load()
    problems = offline_smoke(registry)
    assert problems == []
    for name in REQUIRED_CONTROLS:
        assert name in registry.controls
        assert registry.controls[name].strategies


def test_smoke_cli_offline_exits_zero() -> None:
    from click.testing import CliRunner

    from scripts.publish.smoke_selectors import main

    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "SMOKE OK" in result.output
