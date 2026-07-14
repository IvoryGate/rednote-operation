import json
from datetime import datetime
from pathlib import Path

import click

from src.core.browser import Browser
from src.core.config import config
from src.core.crawl_parse import extract_notes_from_list, page_looks_rejected
from src.core.db import SessionLocal, init_db
from src.core.rate_limit import RateLimiter
from src.models import Keyword


def _limiter() -> RateLimiter:
    c = config.crawl
    return RateLimiter(
        min_interval=c.min_interval_seconds,
        max_interval=c.max_interval_seconds,
        backoff_factor=c.backoff_factor,
        jitter=c.jitter_seconds,
    )


def search_keyword(page, keyword: str, sort: str, count: int, limiter: RateLimiter) -> list[dict]:  # type: ignore[no-untyped-def]
    results: list[dict] = []
    try:
        url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&sort={sort}"
        limiter.wait()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        if page_looks_rejected(page):
            limiter.on_reject()
            click.echo(
                f"  Reject signal for keyword={keyword}; backoff={limiter.current_interval:.1f}s"
            )
            return results
        limiter.on_success()
        cards = extract_notes_from_list(page)
        for item in cards[:count]:
            item = dict(item)
            item["keyword"] = keyword
            results.append(item)
    except Exception as exc:
        click.echo(f"  Search failed for {keyword}: {exc}")
        limiter.on_reject()
    return results


@click.command()
@click.option("--keyword", "-k", multiple=True, help="Search keyword")
@click.option("--keywords-file", type=click.Path(exists=True), help="File with keywords")
@click.option("--count", "-n", default=30, show_default=True, help="Results per keyword")
@click.option("--sort", type=click.Choice(["general", "hot", "latest"]), default="general")
@click.option("--days", default=7, help="Look back days")
@click.option("--output", "-o", type=click.Path(), help="Output JSON file")
@click.option("--db", "to_db", is_flag=True, help="Store in database")
@click.option("--list-trending", is_flag=True, help="List recent trending keywords")
@click.option("--headless", is_flag=True, help="Run browser headless")
@click.option("--account", "session_account", default="main", help="Session account name")
def main(  # type: ignore[no-untyped-def]
    keyword,
    keywords_file,
    count,
    sort,
    days,
    output,
    to_db,
    list_trending,
    headless,
    session_account,
) -> None:
    """Search trending topics and notes on Xiaohongshu."""
    del days  # reserved for future date filtering
    keywords = list(keyword)
    limiter = _limiter()

    if keywords_file:
        with open(keywords_file) as f:
            keywords.extend(line.strip() for line in f if line.strip())

    if list_trending:
        init_db()
        db = SessionLocal()
        recent = (
            db.query(Keyword)
            .filter(Keyword.is_active)
            .order_by(Keyword.updated_at.desc())
            .limit(20)
            .all()
        )
        for k in recent:
            click.echo(f"{k.keyword} (volume: {k.search_volume}, competition: {k.competition})")
        db.close()
        return

    if not keywords:
        click.echo("Provide --keyword or --keywords-file")
        return

    all_results: dict[str, list] = {}
    with Browser(headless=headless or None) as browser:
        ctx = browser.session_context(session_account, rotate_identity=True)
        page = ctx.new_page()
        for kw in keywords:
            click.echo(f"Searching: {kw}")
            results = search_keyword(page, kw, sort, count, limiter)
            all_results[kw] = results
            click.echo(f"  Found {len(results)} notes")

    if to_db:
        init_db()
        db = SessionLocal()
        try:
            for kw, results in all_results.items():
                keyword_entry = db.query(Keyword).filter(Keyword.keyword == kw).first()
                if not keyword_entry:
                    keyword_entry = Keyword(keyword=kw, search_volume=len(results))
                    db.add(keyword_entry)
                else:
                    keyword_entry.search_volume = len(results)
                keyword_entry.updated_at = datetime.now()
            db.commit()
        finally:
            db.close()

    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in all_results.values())
    click.echo(f"Searched {len(keywords)} keywords, total results: {total}")


if __name__ == "__main__":
    main()
