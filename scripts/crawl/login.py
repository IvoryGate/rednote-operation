"""Login session management for Xiaohongshu."""

import click

from src.core.browser import Browser
from src.core.session import SessionManager


@click.group()
def cli() -> None:
    """Manage Xiaohongshu login sessions."""
    pass


@cli.command()
@click.option("--account", default="main", help="Account name")
@click.option("--headless", is_flag=True, help="Run in headless mode")
@click.option("--force", is_flag=True, help="Force re-login")
def login(account: str, headless: bool, force: bool) -> None:
    """Login to Xiaohongshu and save session."""
    session = SessionManager(account)

    if force:
        session.clear_session()
        click.echo("Cleared saved session")

    if session.has_session() and not force:
        click.echo(f"Session exists for '{account}'. Use --force to re-login.")
        return

    click.echo("Opening Xiaohongshu login page...")
    click.echo("Please log in manually, then press Enter.")
    with Browser() as browser:
        browser.start()
        ctx = browser.context(user_data_dir=session.get_user_data_dir())
        page = ctx.new_page()
        page.goto("https://www.xiaohongshu.com/login")
        page.wait_for_url("https://www.xiaohongshu.com/explore", timeout=0)
        state = ctx.storage_state()
        session.save_state(state)
        click.echo(f"Login OK. Session saved for '{account}'.")


@cli.command()
@click.option("--account", default="main", help="Account name")
def status(account: str) -> None:
    """Check login status."""
    session = SessionManager(account)
    if session.has_session():
        click.echo(f"Session exists for '{account}'.")
    else:
        click.echo(f"No session for '{account}'. Run `login login` first.")


if __name__ == "__main__":
    cli()
