"""Tests for account config loading and login-status heuristics."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.core.accounts import (
    DEFAULT_ACCOUNT_NAME,
    default_account_name,
    get_account,
    load_accounts,
    resolve_cookies_path,
)
from src.core.session import check_login_status


def test_load_accounts_missing_file(tmp_path: Path) -> None:
    assert load_accounts(tmp_path / "missing.yaml") == []


def test_load_accounts_and_get(tmp_path: Path) -> None:
    path = tmp_path / "accounts.yaml"
    path.write_text(
        yaml.dump(
            {
                "accounts": [
                    {
                        "name": "main",
                        "phone": "13800000000",
                        "cookies_path": "./.browser-data/main",
                        "enabled": True,
                    },
                    {"name": "backup", "enabled": False},
                ]
            }
        )
    )
    accounts = load_accounts(path)
    assert len(accounts) == 2
    assert accounts[0].name == "main"
    assert get_account("backup", path) is not None
    assert get_account("missing", path) is None
    assert default_account_name(path) == "main"
    assert resolve_cookies_path(accounts[0]) == "./.browser-data/main"
    assert resolve_cookies_path(accounts[1]) == "./.browser-data/backup"


def test_default_account_name_falls_back() -> None:
    assert default_account_name("/nonexistent/accounts.yaml") == DEFAULT_ACCOUNT_NAME


def test_default_skips_disabled(tmp_path: Path) -> None:
    path = tmp_path / "accounts.yaml"
    path.write_text(
        yaml.dump(
            {
                "accounts": [
                    {"name": "old", "enabled": False},
                    {"name": "active", "enabled": True},
                ]
            }
        )
    )
    assert default_account_name(path) == "active"


class _FakePage:
    def __init__(self, url: str, html: str) -> None:
        self.url = url
        self._html = html
        self.goto_urls: list[str] = []

    def goto(self, url: str, **kwargs: object) -> None:
        self.goto_urls.append(url)
        # Simulate login redirect
        if "login" in self.url:
            pass

    def wait_for_timeout(self, _ms: int) -> None:
        return None

    def content(self) -> str:
        return self._html


def test_check_login_status_true_on_creator_markers() -> None:
    page = _FakePage(
        "https://creator.xiaohongshu.com/new/home",
        "<html>创作者中心 发布笔记</html>",
    )
    assert check_login_status(page) is True
    assert page.goto_urls


def test_check_login_status_false_on_login_redirect() -> None:
    page = _FakePage(
        "https://creator.xiaohongshu.com/login",
        "<html>请登录</html>",
    )
    assert check_login_status(page) is False
