"""Local first-run preflight: accounts, session files, offline smokes.

Does not open Xiaohongshu or require a display — prints the next live commands.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import click

from src.core.accounts import default_account_name, load_accounts
from src.core.publish_dom import SelectorRegistry, offline_smoke
from src.core.session import SessionManager


def _check_accounts() -> tuple[bool, str, str]:
    path = Path("config/accounts.yaml")
    if not path.exists():
        return (
            False,
            "missing",
            "cp config/accounts.yaml.template config/accounts.yaml",
        )
    accounts = load_accounts(path)
    enabled = [a.name for a in accounts if a.enabled]
    if not accounts:
        return False, "empty", "accounts.yaml has no accounts[] entries"
    if not enabled:
        return False, "none-enabled", "enable at least one account (enabled: true)"
    return True, "ok", f"enabled={','.join(enabled)} default={default_account_name()}"


def _check_session(account: str) -> tuple[bool, str]:
    session = SessionManager(account)
    if session.has_session():
        return True, f"session file present for '{account}'"
    return False, (
        f"no session for '{account}' — "
        f"uv run python scripts/crawl/login.py login --account {account}"
    )


def _run_offline_smokes() -> list[str]:
    problems: list[str] = []
    registry = SelectorRegistry.load()
    problems.extend(offline_smoke(registry))

    # Tiny fixture so probe CLI path is exercised without live browser.
    sample = [
        {
            "title": "sample-hit",
            "view_count": 100,
            "view_count_found": True,
            "like_count": 1,
            "like_count_found": True,
        },
        {
            "title": "sample-miss",
            "view_count": 0,
            "view_count_found": False,
            "like_count": 2,
            "like_count_found": True,
        },
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "notes.json"
        path.write_text(json.dumps(sample), encoding="utf-8")
        from click.testing import CliRunner

        from scripts.crawl.probe_view_count import main as probe_main

        result = CliRunner().invoke(probe_main, ["--input", str(path)])
        if result.exit_code != 0:
            problems.append(f"probe offline failed: {result.output.strip()}")
    return problems


@click.command()
@click.option(
    "--account",
    default=None,
    help="Account to check session for (default: first enabled / main)",
)
@click.option("--skip-smoke", is_flag=True, help="Skip offline smoke / probe")
def main(account: str | None, skip_smoke: bool) -> None:
    """Check local prerequisites for first live run."""
    ok_accounts, accounts_status, accounts_detail = _check_accounts()
    click.echo(f"[accounts] {accounts_status}: {accounts_detail}")

    account_name = account or default_account_name()
    session_ok, session_detail = _check_session(account_name)
    click.echo(f"[session]  {'ok' if session_ok else 'missing'}: {session_detail}")

    smoke_ok = True
    if not skip_smoke:
        problems = _run_offline_smokes()
        if problems:
            smoke_ok = False
            click.echo("[smoke]   FAIL")
            for problem in problems:
                click.echo(f"  - {problem}")
        else:
            click.echo("[smoke]   offline publish selectors + view probe OK")

    click.echo("")
    if ok_accounts and session_ok and smoke_ok:
        click.echo("PREFLIGHT OK — next live steps:")
    else:
        click.echo("PREFLIGHT incomplete — fix items above, then:")

    click.echo(f"  uv run python scripts/crawl/login.py status --account {account_name}")
    click.echo(
        "  uv run python scripts/publish/smoke_selectors.py "
        f"--live --account {account_name} --headless"
    )
    click.echo(
        "  uv run python scripts/crawl/probe_view_count.py "
        f"--live -k 美食 -n 20 --account {account_name} --headless"
    )
    click.echo("See docs/first_run.md for the full checklist.")

    if not (ok_accounts and session_ok and smoke_ok):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
