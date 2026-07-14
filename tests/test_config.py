# mypy: ignore-errors
from pathlib import Path

import yaml

from src.core.config import Config


def test_config_defaults() -> None:
    cfg = Config()
    assert cfg.database.url == "sqlite:///database/rednote.db"
    assert cfg.database.echo is False
    assert cfg.browser.headless is False
    assert cfg.browser.slow_mo == 100
    assert cfg.browser.timeout == 30000
    assert cfg.app.name == "RedNote Operation"


def test_config_from_yaml(tmp_path: Path) -> None:
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        yaml.dump(
            {
                "database": {"url": "sqlite:///test.db", "echo": True},
                "browser": {"headless": True, "timeout": 15000},
            }
        )
    )
    cfg = Config.from_yaml(yaml_path)
    assert cfg.database.url == "sqlite:///test.db"
    assert cfg.database.echo is True
    assert cfg.browser.headless is True
    assert cfg.browser.timeout == 15000


def test_config_missing_fields_default(tmp_path: Path) -> None:
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text("database:\n  url: sqlite:///test.db\n")
    cfg = Config.from_yaml(yaml_path)
    assert cfg.database.url == "sqlite:///test.db"
    assert cfg.database.echo is False
    assert cfg.browser.headless is False


def test_config_from_nonexistent_yaml(tmp_path: Path) -> None:
    cfg = Config.from_yaml(tmp_path / "nonexistent.yaml")
    assert cfg.database.url == "sqlite:///database/rednote.db"
