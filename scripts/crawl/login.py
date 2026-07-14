"""Login session management for Xiaohongshu."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import click

from src.core.accounts import default_account_name, get_account, load_accounts
from src.core.browser import DESKTOP_UA, DESKTOP_VIEWPORT, Browser
from src.core.session import SessionManager, check_login_status, check_www_login_status


def _wait_until(
    probe: Callable[[], bool],
    *,
    label: str,
    timeout_s: int,
    interval_s: float = 5.0,
) -> bool:
    """Poll ``probe()`` until True or timeout. Prints progress for scan/login."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if probe():
            click.echo(f"{label}: OK")
            return True
        remaining = max(0, int(deadline - time.time()))
        click.echo(f"{label}: waiting… ({remaining}s left)")
        time.sleep(interval_s)
    return False


@click.group()
def cli() -> None:
    """Manage Xiaohongshu login sessions."""
    pass


@cli.command("list")
def list_accounts() -> None:
    """List accounts from config/accounts.yaml."""
    accounts = load_accounts()
    if not accounts:
        click.echo("No accounts.yaml found.")
        click.echo("  cp config/accounts.yaml.template config/accounts.yaml")
        click.echo("See docs/first_run.md for the full checklist.")
        return
    for account in accounts:
        flag = "on" if account.enabled else "off"
        click.echo(f"{account.name}\tenabled={flag}\tplatform={account.platform}")


def _resolve_account(account: str | None) -> str:
    return account or default_account_name()


def _warn_if_unknown(account_name: str) -> None:
    if not Path("config/accounts.yaml").exists():
        click.echo(
            f"Warning: config/accounts.yaml missing — "
            f"using '{account_name}' for session path only.\n"
            "  cp config/accounts.yaml.template config/accounts.yaml\n"
            "  See docs/first_run.md"
        )
        return
    cfg = get_account(account_name)
    if cfg is None:
        click.echo(f"Warning: account '{account_name}' not listed in accounts.yaml")
    elif not cfg.enabled:
        click.echo(f"Warning: account '{account_name}' is disabled in accounts.yaml")


@cli.command()
@click.option(
    "--account",
    default=None,
    help="Account name (default: first enabled in accounts.yaml, else main)",
)
@click.option("--headless", is_flag=True, help="Run in headless mode")
@click.option("--force", is_flag=True, help="Force re-login")
@click.option(
    "--wait-seconds",
    default=180,
    show_default=True,
    help="Seconds to wait for manual scan/login on each step",
)
def login(account: str | None, headless: bool, force: bool, wait_seconds: int) -> None:
    """Login to Xiaohongshu and save session (creator + www)."""
    account_name = _resolve_account(account)
    _warn_if_unknown(account_name)
    session = SessionManager(account_name)

    if force:
        session.clear_session()
        click.echo("Cleared saved session")

    if session.has_session() and not force:
        click.echo(f"Session file exists for '{account_name}'. Verifying...")
        browser = Browser()
        browser.start(headless=True)
        try:
            ctx = browser.session_context(
                account_name,
                viewport=DESKTOP_VIEWPORT,
                user_agent=DESKTOP_UA,
                rotate_identity=False,
            )
            page = ctx.new_page()
            creator_ok = check_login_status(page)
            www_ok = check_www_login_status(page) if creator_ok else False
            if creator_ok and www_ok:
                click.echo(
                    f"Already logged in as '{account_name}' "
                    "(creator + www). Use --force to re-login."
                )
                return
            if creator_ok and not www_ok:
                click.echo(
                    "Creator session OK, but www search still needs login — "
                    "continuing to capture consumer cookies."
                )
            else:
                click.echo("Saved session is stale; starting fresh login.")
                session.clear_session()
        finally:
            browser.close()

    click.echo("Opening Xiaohongshu login pages (desktop viewport)...")
    click.echo("1) Creator login  2) www search login (if QR wall appears)")
    browser = Browser()
    # Interactive scan/login needs a visible window unless --headless.
    browser.start(headless=headless)
    try:
        ctx = browser.session_context(
            account_name,
            viewport=DESKTOP_VIEWPORT,
            user_agent=DESKTOP_UA,
            rotate_identity=False,
        )
        page = ctx.new_page()
        creator_ok = session.has_session() and check_login_status(page)
        if not creator_ok:
            page.goto("https://creator.xiaohongshu.com/login")
            click.echo("Complete creator login in the browser window…")
            creator_ok = _wait_until(
                lambda: check_login_status(page),
                label="creator",
                timeout_s=wait_seconds,
            )
            if not creator_ok:
                click.echo("Creator login check failed — session may be incomplete.")

        click.echo("Opening www search to capture consumer cookies...")
        if not check_www_login_status(page):
            click.echo("Scan/login on the www search QR wall if it appears…")
            www_ok = _wait_until(
                lambda: check_www_login_status(page),
                label="www",
                timeout_s=wait_seconds,
            )
            if not www_ok:
                click.echo("www login check still failing — crawl probes may not work.")

        state = ctx.storage_state()
        session.save_state(state)
        click.echo(f"Login OK. Session saved for '{account_name}'.")
    finally:
        browser.close()


@cli.command()
@click.option(
    "--account",
    default=None,
    help="Account name (default: first enabled in accounts.yaml, else main)",
)
@click.option("--headless/--no-headless", default=True, help="Browser visibility")
def status(account: str | None, headless: bool) -> None:
    """Check login status (session file + live creator page probe)."""
    account_name = _resolve_account(account)
    session = SessionManager(account_name)
    if not session.has_session():
        click.echo(f"No session for '{account_name}'. Run `login login` first.")
        return

    click.echo(f"Session file exists for '{account_name}'. Probing creator + www...")
    browser = Browser()
    browser.start(headless=headless)
    try:
        ctx = browser.session_context(
            account_name,
            viewport=DESKTOP_VIEWPORT,
            user_agent=DESKTOP_UA,
            rotate_identity=False,
        )
        page = ctx.new_page()
        creator_ok = check_login_status(page)
        www_ok = check_www_login_status(page) if creator_ok else False
    finally:
        browser.close()

    if creator_ok and www_ok:
        click.echo(f"Logged in: '{account_name}' (creator + www)")
    elif creator_ok:
        click.echo(
            f"Partial login: '{account_name}' creator OK, www search locked. "
            "Re-run login (www QR step)."
        )
    else:
        click.echo(f"Session stale / logged out: '{account_name}'. Re-run login --force.")


if __name__ == "__main__":
    cli()
