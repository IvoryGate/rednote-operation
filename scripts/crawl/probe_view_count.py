"""Probe view_count (and like_count) extraction hit-rate from crawl results.

Offline: pass a JSON export from search/collect scripts.
Live: open a keyword search with a saved session and score freshly parsed cards.

Exit code 0 always when stats are produced; use --min-hit-rate to fail CI-style
gates (offline fixtures recommended — live UI may omit view counts on cards).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from src.core.crawl_parse import metric_hit_stats


def _load_notes(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("notes", "results", "items", "data"):
            nested = data.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    raise click.ClickException(f"Unsupported JSON shape in {path}")


def _live_notes(keyword: str, count: int, account: str, headless: bool) -> list[dict[str, Any]]:
    from src.core.browser import Browser
    from src.core.config import config
    from src.core.crawl_parse import extract_notes_from_list, page_looks_rejected
    from src.core.rate_limit import RateLimiter
    from src.core.session import SessionManager

    session = SessionManager(account)
    if not session.has_session():
        raise click.ClickException(f"no session for '{account}' — run scripts/crawl/login.py first")

    limiter = RateLimiter(
        min_interval=config.crawl.min_interval_seconds,
        max_interval=config.crawl.max_interval_seconds,
        backoff_factor=config.crawl.backoff_factor,
        jitter=config.crawl.jitter_seconds,
    )
    from src.core.browser import DESKTOP_UA

    browser = Browser()
    browser.start(headless=headless)
    try:
        # Desktop identity (default). Mobile UA/viewport often hits the
        # www search QR wall even when creator cookies are present.
        ctx = browser.session_context(account, user_agent=DESKTOP_UA)
        page = ctx.new_page()
        limiter.wait()
        page.goto(
            f"https://www.xiaohongshu.com/search_result?keyword={keyword}&sort=general",
            wait_until="domcontentloaded",
        )
        page.wait_for_timeout(2500)
        if page_looks_rejected(page):
            limiter.on_reject()
            raise click.ClickException("page looks rejected (captcha / login / rate-limit)")
        limiter.on_success()
        notes = extract_notes_from_list(page)
        return notes[:count]
    finally:
        browser.close()


def _print_report(
    mode: str, notes: list[dict[str, Any]], fields: tuple[str, ...]
) -> dict[str, Any]:
    report: dict[str, Any] = {"mode": mode, "note_count": len(notes), "metrics": {}}
    for field in fields:
        stats = metric_hit_stats(notes, field=field)
        report["metrics"][field] = stats
        click.echo(
            f"{field}: hits={stats['hits']}/{stats['total']} "
            f"hit_rate={stats['hit_rate']:.1%} "
            f"positive_rate={stats['positive_rate']:.1%}"
        )
    return report


@click.command()
@click.option(
    "--input", "input_path", type=click.Path(exists=True, path_type=Path), help="JSON notes export"
)
@click.option("--live", is_flag=True, help="Crawl a keyword search with a saved session")
@click.option("--keyword", "-k", default="美食", show_default=True, help="Live search keyword")
@click.option("--count", "-n", default=20, show_default=True, help="Max notes to score")
@click.option("--account", default="main", show_default=True)
@click.option("--headless/--no-headless", default=True)
@click.option(
    "--min-hit-rate",
    type=float,
    default=None,
    help="Fail if view_count hit_rate is below this (0-1)",
)
@click.option("--json-out", type=click.Path(path_type=Path), help="Write report JSON")
def main(
    input_path: Path | None,
    live: bool,
    keyword: str,
    count: int,
    account: str,
    headless: bool,
    min_hit_rate: float | None,
    json_out: Path | None,
) -> None:
    """Report view_count extraction hit-rate (offline JSON or live search)."""
    if live and input_path:
        raise click.ClickException("pass either --input or --live, not both")
    if not live and input_path is None:
        raise click.ClickException("provide --input PATH.json or --live")

    if live:
        notes = _live_notes(keyword, count, account, headless)
        mode = "live"
    else:
        assert input_path is not None
        notes = _load_notes(input_path)[:count]
        mode = "offline"

    if not notes:
        raise click.ClickException("no notes to score")

    report = _print_report(mode, notes, ("view_count", "like_count"))
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        click.echo(f"Wrote {json_out}")

    if min_hit_rate is not None:
        rate = float(report["metrics"]["view_count"]["hit_rate"])
        if rate < min_hit_rate:
            click.echo(f"FAIL: view_count hit_rate {rate:.1%} < min {min_hit_rate:.1%}", err=True)
            sys.exit(1)
    click.echo("PROBE OK")


if __name__ == "__main__":
    main()
