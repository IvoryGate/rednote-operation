# mypy: ignore-errors
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_playwright():
    with patch("src.core.browser.sync_playwright") as mock:
        yield mock


def test_browser_start_close(mock_playwright) -> None:
    mock_pw = MagicMock()
    mock_browser = MagicMock()
    mock_playwright.return_value.__enter__.return_value = mock_pw
    mock_pw.chromium.launch.return_value = mock_browser

    from src.core.browser import Browser

    browser = Browser()
    browser.start()
    assert browser._browser is not None
    assert browser._playwright is not None

    browser.close()
    mock_browser.close.assert_called_once()
    mock_pw.stop.assert_called_once()


def test_browser_context_creates_new_context(mock_playwright) -> None:
    mock_pw = MagicMock()
    mock_browser = MagicMock()
    mock_playwright.return_value.__enter__.return_value = mock_pw
    mock_pw.chromium.launch.return_value = mock_browser

    from src.core.browser import DESKTOP_UA, DESKTOP_VIEWPORT, Browser

    browser = Browser()
    browser.start(headless=True)
    ctx = browser.context()

    assert ctx is not None
    mock_browser.new_context.assert_called_once()
    kwargs = mock_browser.new_context.call_args.kwargs
    assert kwargs.get("viewport") == DESKTOP_VIEWPORT
    assert kwargs.get("user_agent") == DESKTOP_UA
    assert kwargs.get("no_viewport") is None


def test_browser_headed_context_uses_no_viewport(mock_playwright) -> None:
    mock_pw = MagicMock()
    mock_browser = MagicMock()
    mock_playwright.return_value.__enter__.return_value = mock_pw
    mock_pw.chromium.launch.return_value = mock_browser

    from src.core.browser import Browser

    browser = Browser()
    browser.start(headless=False)
    browser.context()

    kwargs = mock_browser.new_context.call_args.kwargs
    assert kwargs.get("no_viewport") is True
    assert "viewport" not in kwargs or kwargs.get("viewport") is None
    launch_kwargs = mock_pw.chromium.launch.call_args.kwargs
    assert "--start-maximized" in (launch_kwargs.get("args") or [])


def test_browser_context_requires_start() -> None:
    from src.core.browser import Browser

    browser = Browser()
    with pytest.raises(RuntimeError, match="Browser not started"):
        browser.context()


def test_browser_context_manager(mock_playwright) -> None:
    mock_pw = MagicMock()
    mock_browser = MagicMock()
    mock_playwright.return_value.__enter__.return_value = mock_pw
    mock_pw.chromium.launch.return_value = mock_browser

    from src.core.browser import Browser

    with Browser() as browser:
        browser.start()
        assert browser._browser is not None

    mock_browser.close.assert_called_once()


def test_browser_context_with_storage_state(mock_playwright, tmp_path: Path) -> None:
    mock_pw = MagicMock()
    mock_browser = MagicMock()
    mock_playwright.return_value.__enter__.return_value = mock_pw
    mock_pw.chromium.launch.return_value = mock_browser

    from src.core.browser import Browser

    browser = Browser()
    browser.start()

    state_file = tmp_path / "state.json"
    state_file.write_text("{}")

    ctx = browser.context(storage_state=str(state_file))
    assert ctx is not None
    mock_browser.new_context.assert_called_once()
    call_kwargs = mock_browser.new_context.call_args.kwargs
    assert call_kwargs.get("storage_state") == str(state_file)
