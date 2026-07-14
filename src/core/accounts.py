"""Load local account configs from config/accounts.yaml (gitignored)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

DEFAULT_ACCOUNTS_PATH = Path("config/accounts.yaml")
DEFAULT_ACCOUNT_NAME = "main"


class AccountConfig(BaseModel):
    name: str
    phone: str | None = None
    cookies_path: str | None = None
    platform: str = "xiaohongshu"
    enabled: bool = True


class AccountsFile(BaseModel):
    accounts: list[AccountConfig] = Field(default_factory=list)


def load_accounts(path: str | Path = DEFAULT_ACCOUNTS_PATH) -> list[AccountConfig]:
    """Return accounts from YAML, or an empty list when the file is absent."""
    config_path = Path(path)
    if not config_path.exists():
        return []
    with open(config_path) as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return AccountsFile.model_validate(data).accounts


def get_account(
    name: str,
    path: str | Path = DEFAULT_ACCOUNTS_PATH,
) -> AccountConfig | None:
    for account in load_accounts(path):
        if account.name == name:
            return account
    return None


def default_account_name(path: str | Path = DEFAULT_ACCOUNTS_PATH) -> str:
    """First enabled account name, else ``main`` (matches CLI defaults)."""
    for account in load_accounts(path):
        if account.enabled:
            return account.name
    return DEFAULT_ACCOUNT_NAME


def resolve_cookies_path(account: AccountConfig) -> str:
    if account.cookies_path:
        return account.cookies_path
    return f"./.browser-data/{account.name}"
