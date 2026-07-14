from pathlib import Path
from typing import Any, Self

from playwright.sync_api import Browser as PlaywrightBrowser
from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright

from src.core.config import config
from src.core.headers import default_header_pool

# Default identity is desktop. Mobile is opt-in only (explicit viewport/UA).
DESKTOP_VIEWPORT = {"width": 1920, "height": 1080}
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
    def __init__(self, headless: bool | None = None) -> None:
        self._playwright: Playwright | None = None
        self._browser: PlaywrightBrowser | None = None
        self._context: BrowserContext | None = None
        self._headless: bool | None = None
        self._headless_opt = headless

    def start(self, headless: bool | None = None) -> Self:
        ctx_mgr = sync_playwright()
        self._playwright = ctx_mgr.__enter__()
        resolved = headless if headless is not None else self._headless_opt
        self._headless = resolved if resolved is not None else config.browser.headless
        launch_args: list[str] = []
        if not self._headless:
            # Match a normal maximized desktop window (not phone chrome).
            launch_args.append("--start-maximized")
        self._browser = self._playwright.chromium.launch(
            headless=self._headless,
            slow_mo=config.browser.slow_mo,
            args=launch_args or None,
        )
        return self

    def context(
        self,
        user_data_dir: str | None = None,
        storage_state: str | None = None,
        viewport: dict | None = None,
        user_agent: str | None = None,
        extra_headers: dict[str, str] | None = None,
        *,
        rotate_identity: bool = False,
        mobile: bool = False,
    ) -> BrowserContext:
        if self._browser is None:
            raise RuntimeError("Browser not started. Call .start() first.")

        if user_data_dir:
            context_path = Path(user_data_dir)
            context_path.mkdir(parents=True, exist_ok=True)

        state = storage_state or (
            str(Path(user_data_dir) / "state.json") if user_data_dir else None
        )

        headers = dict(extra_headers or {})
        ua = user_agent
        if rotate_identity:
            identity = default_header_pool.next_headers()
            ua = ua or identity["User-Agent"]
            headers.setdefault("Accept-Language", identity["Accept-Language"])
            headers.setdefault("Accept", identity["Accept"])

        ctx_kwargs: dict[str, Any] = {
            "user_agent": ua or (MOBILE_UA if mobile else DESKTOP_UA),
            "storage_state": state if state and Path(state).exists() else None,
            "extra_http_headers": headers or None,
        }
        if viewport is not None:
            ctx_kwargs["viewport"] = viewport
        elif mobile:
            ctx_kwargs["viewport"] = MOBILE_VIEWPORT
        elif self._headless:
            # Headless has no real window — pin a full-HD desktop size.
            ctx_kwargs["viewport"] = DESKTOP_VIEWPORT
        else:
            # Headed: use the maximized OS window (fullscreen-class proportions).
            ctx_kwargs["no_viewport"] = True

        self._context = self._browser.new_context(**ctx_kwargs)
        return self._context

    def session_context(
        self,
        account_name: str = "main",
        viewport: dict | None = None,
        user_agent: str | None = None,
        *,
        rotate_identity: bool = False,
        mobile: bool = False,
    ) -> BrowserContext:
        """Create a context with a saved session for the given account.

        Defaults to desktop identity. Pass ``mobile=True`` only when you
        intentionally want phone layout.
        """
        from src.core.session import SessionManager

        session = SessionManager(account_name)
        return self.context(
            user_data_dir=session.get_user_data_dir(),
            storage_state=str(session.state_file) if session.has_session() else None,
            viewport=viewport,
            user_agent=user_agent,
            rotate_identity=rotate_identity,
            mobile=mobile,
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
        return self.start(headless=self._headless_opt)

    def __exit__(self, *args: object) -> None:
        self.close()
