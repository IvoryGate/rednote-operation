from pathlib import Path
from typing import Self

from playwright.sync_api import Browser as PlaywrightBrowser
from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright

from src.core.config import config


class Browser:
    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: PlaywrightBrowser | None = None
        self._context: BrowserContext | None = None

    def start(self) -> Self:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=config.browser.headless,
            slow_mo=config.browser.slow_mo,
        )
        return self

    def context(self, user_data_dir: str | None = None) -> BrowserContext:
        if self._browser is None:
            raise RuntimeError("Browser not started. Call .start() first.")

        if user_data_dir:
            context_path = Path(user_data_dir)
            context_path.mkdir(parents=True, exist_ok=True)

        self._context = self._browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            storage_state=str(Path(user_data_dir) / "state.json") if user_data_dir else None,
        )
        return self._context

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
