import json
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from src.core.config import config


class SessionManager:
    def __init__(self, account_name: str = "main") -> None:
        self.account_name = account_name
        self.state_dir = Path(config.browser.user_data_dir) / account_name
        self.state_file = self.state_dir / "state.json"

    def ensure_dir(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: dict) -> None:
        self.ensure_dir()
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self) -> dict | None:
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return None

    def has_session(self) -> bool:
        return self.state_file.exists()

    def clear_session(self) -> None:
        if self.state_file.exists():
            self.state_file.unlink()

    def get_user_data_dir(self) -> str:
        self.ensure_dir()
        return str(self.state_dir)


_LOGGED_IN_MARKERS = (
    "创作者中心",
    "发布笔记",
    "数据概览",
    "内容管理",
    "创作灵感",
)

_WWW_LOGIN_WALL_MARKERS = (
    "登录后查看搜索结果",
    "登录后查看",
    "可用 小红书 或 微信 扫码",
)


def check_login_status(page: Any) -> bool:
    """Return True when the Playwright page has an active creator session.

    Navigates to the creator home. A redirect to ``/login`` (or captcha) means
    logged out; presence of creator-console markers means logged in.
    """
    try:
        page.goto(
            "https://creator.xiaohongshu.com/new/home",
            wait_until="domcontentloaded",
            timeout=config.browser.timeout,
        )
        page.wait_for_timeout(1500)
        url = (page.url or "").lower()
        if "login" in url or "captcha" in url:
            return False

        html = page.content()
        if any(marker in html for marker in _LOGGED_IN_MARKERS):
            return True

        # Creator host without login redirect is a weak positive signal.
        return "creator.xiaohongshu.com" in url and "login" not in url
    except Exception:
        return False


def check_www_login_status(page: Any, *, keyword: str = "美食") -> bool:
    """Return True when www search is usable (no QR / login wall).

    Creator cookies alone often do not unlock ``www.xiaohongshu.com`` search —
    consumers need a separate web login in the same storage_state.
    """
    try:
        page.goto(
            f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}&sort=general",
            wait_until="domcontentloaded",
            timeout=config.browser.timeout,
        )
        page.wait_for_timeout(2500)
        url = (page.url or "").lower()
        if "login" in urlparse(url).path or "captcha" in url:
            return False

        html = page.content()
        if any(marker in html for marker in _WWW_LOGIN_WALL_MARKERS):
            return False

        cards = page.query_selector_all(
            "section.note-item, section.reds-note-card, .note-item, [class*=note-item]"
        )
        return len(cards) > 0
    except Exception:
        return False
