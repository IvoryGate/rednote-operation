"""Login session management for Xiaohongshu."""

from pathlib import Path

import click

from src.core.accounts import default_account_name, get_account, load_accounts
from src.core.browser import Browser
from src.core.session import SessionManager, check_login_status


@click.group()
def cli() -> None:
    """Manage Xiaohongshu login sessions."""
    pass


@cli.command("list")
def list_accounts() -> None:
    """List accounts from config/accounts.yaml."""
    accounts = load_accounts()
    if not accounts:
        click.echo("No accounts.yaml found. Copy config/accounts.yaml.template first.")
        return
    for account in accounts:
        flag = "on" if account.enabled else "off"
        click.echo(f"{account.name}\tenabled={flag}\tplatform={account.platform}")


def _resolve_account(account: str | None) -> str:
    return account or default_account_name()


def _warn_if_unknown(account_name: str) -> None:
    if not Path("config/accounts.yaml").exists():
        click.echo(
            f"Warning: config/accounts.yaml missing — using '{account_name}' for session path only."
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
def login(account: str | None, headless: bool, force: bool) -> None:
    """Login to Xiaohongshu and save session."""
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
            ctx = browser.session_context(account_name)
            page = ctx.new_page()
            if check_login_status(page):
                click.echo(f"Already logged in as '{account_name}'. Use --force to re-login.")
                return
            click.echo("Saved session is stale; starting fresh login.")
            session.clear_session()
        finally:
            browser.close()

    click.echo("Opening Xiaohongshu login page...")
    click.echo("Please log in manually, then press Enter.")
    browser = Browser()
    browser.start(headless=headless)
    try:
        ctx = browser.session_context(account_name)
        page = ctx.new_page()
        page.goto("https://creator.xiaohongshu.com/login")
        input("After logging in, press Enter to save session...")
        if not check_login_status(page):
            click.echo("Login check failed — session may be incomplete. Saving anyway.")
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

    click.echo(f"Session file exists for '{account_name}'. Probing creator home...")
    browser = Browser()
    browser.start(headless=headless)
    try:
        ctx = browser.session_context(account_name)
        page = ctx.new_page()
        ok = check_login_status(page)
    finally:
        browser.close()

    if ok:
        click.echo(f"Logged in: '{account_name}'")
    else:
        click.echo(f"Session stale / logged out: '{account_name}'. Re-run login --force.")


if __name__ == "__main__":
    cli()
