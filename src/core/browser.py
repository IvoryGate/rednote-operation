from pathlib import Path
from typing import Self

from playwright.sync_api import Browser as PlaywrightBrowser
from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright

from src.core.config import config

DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
MOBILE_VIEWPORT = {"width": 390, "height": 844}
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)


class Browser:
    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: PlaywrightBrowser | None = None
        self._context: BrowserContext | None = None
        self._headless: bool | None = None

    def start(self, headless: bool | None = None) -> Self:
        ctx_mgr = sync_playwright()
        self._playwright = ctx_mgr.__enter__()
        self._headless = headless if headless is not None else config.browser.headless
        self._browser = self._playwright.chromium.launch(
            headless=self._headless,
            slow_mo=config.browser.slow_mo,
        )
        return self

    def context(
        self,
        user_data_dir: str | None = None,
        storage_state: str | None = None,
        viewport: dict | None = None,
        user_agent: str | None = None,
    ) -> BrowserContext:
        if self._browser is None:
            raise RuntimeError("Browser not started. Call .start() first.")

        if user_data_dir:
            context_path = Path(user_data_dir)
            context_path.mkdir(parents=True, exist_ok=True)

        state = storage_state or (
            str(Path(user_data_dir) / "state.json") if user_data_dir else None
        )

        self._context = self._browser.new_context(
            viewport=viewport or MOBILE_VIEWPORT,
            user_agent=user_agent or MOBILE_UA,
            storage_state=state if state and Path(state).exists() else None,
        )
        return self._context

    def session_context(
        self,
        account_name: str = "main",
        viewport: dict | None = None,
        user_agent: str | None = None,
    ) -> BrowserContext:
        """Create a context with a saved session for the given account."""
        from src.core.session import SessionManager

        session = SessionManager(account_name)
        return self.context(
            user_data_dir=session.get_user_data_dir(),
            storage_state=str(session.state_file) if session.has_session() else None,
            viewport=viewport,
            user_agent=user_agent,
        )

    def page(self) -> Page:
        if self._context is None:
            raise RuntimeError("No context. Call .context() first.")
        return self._context.new_page()

    def close(self) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(self, *args: object) -> None:
        self.close()
