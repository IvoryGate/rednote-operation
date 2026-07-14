import json
from pathlib import Path

import click

from src.core.browser import Browser
from src.core.config import config
from src.core.crawl_parse import (
    extract_note_detail,
    extract_notes_from_list,
    note_fields_for_db,
    page_looks_rejected,
)
from src.core.db import SessionLocal, init_db
from src.core.rate_limit import RateLimiter
from src.models import Note


def _limiter() -> RateLimiter:
    c = config.crawl
    return RateLimiter(
        min_interval=c.min_interval_seconds,
        max_interval=c.max_interval_seconds,
        backoff_factor=c.backoff_factor,
        jitter=c.jitter_seconds,
    )


def _goto(page, url: str, limiter: RateLimiter) -> None:  # type: ignore[no-untyped-def]
    limiter.wait()
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    if page_looks_rejected(page):
        limiter.on_reject()
        click.echo(f"  Rate-limit/captcha signal on {url}; backoff={limiter.current_interval:.1f}s")
    else:
        limiter.on_success()


@click.command()
@click.option("--url", "-u", help="Single note URL to collect")
@click.option("--user-id", "-uid", help="User ID to collect notes from")
@click.option("--query", "-q", help="Search keyword")
@click.option("--count", "-n", default=20, show_default=True, help="Max notes to collect")
@click.option("--output", "-o", type=click.Path(), help="Output JSON file")
@click.option("--headless", is_flag=True, help="Run browser headless")
@click.option("--db", "to_db", is_flag=True, help="Store in database")
@click.option("--account", "session_account", default="main", help="Session account name")
def main(  # type: ignore[no-untyped-def]
    url, user_id, query, count, output, headless, to_db, session_account
) -> None:
    """Collect notes from Xiaohongshu."""
    results = []
    limiter = _limiter()

    with Browser(headless=headless or None) as browser:
        ctx = browser.session_context(session_account, rotate_identity=True)
        page = ctx.new_page()

        if url:
            _goto(page, url, limiter)
            data = extract_note_detail(page)
            if data:
                results.append(data)
        elif user_id:
            _goto(page, f"https://www.xiaohongshu.com/user/profile/{user_id}", limiter)
            results = extract_notes_from_list(page)[:count]
        elif query:
            _goto(page, f"https://www.xiaohongshu.com/search_result?keyword={query}", limiter)
            results = extract_notes_from_list(page)[:count]
        else:
            click.echo("Provide --url, --user-id, or --query")
            return

    if to_db and results:
        init_db()
        db = SessionLocal()
        try:
            saved = 0
            for item in results:
                fields = note_fields_for_db(item)
                if not fields.get("note_id"):
                    continue
                existing = db.query(Note).filter(Note.note_id == fields["note_id"]).first()
                if existing:
                    for key, value in fields.items():
                        if key != "note_id" and value is not None:
                            setattr(existing, key, value)
                else:
                    db.add(Note(**fields))
                    saved += 1
            db.commit()
            click.echo(f"Saved {saved} new notes to DB")
        finally:
            db.close()

    if output and results:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    click.echo(f"Collected {len(results)} notes")


if __name__ == "__main__":
    main()
