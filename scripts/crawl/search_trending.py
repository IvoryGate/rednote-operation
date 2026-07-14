import json
from pathlib import Path
from typing import Any

import click

from src.core.browser import Browser
from src.core.db import SessionLocal, init_db
from src.models import Keyword


def search_keyword(page: Any, keyword: str, sort: str, count: int) -> list[dict]:
    results = []
    try:
        url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&sort={sort}"
        page.goto(url)
        page.wait_for_timeout(5000)
        cards = page.query_selector_all("section.reds-note-card")
        for card in cards[:count]:
            title_el = card.query_selector(".note-title")
            img_el = card.query_selector("img")
            results.append(
                {
                    "keyword": keyword,
                    "title": title_el.inner_text() if title_el else "",
                    "cover": img_el.get_attribute("src") if img_el else "",
                }
            )
    except Exception:
        pass
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
    keywords = list(keyword)

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

    all_results = {}
    with Browser() as browser:
        ctx = browser.session_context(session_account)
        page = ctx.new_page()
        for kw in keywords:
            click.echo(f"Searching: {kw}")
            results = search_keyword(page, kw, sort, count)
            all_results[kw] = results
            click.echo(f"  Found {len(results)} notes")

    if to_db:
        init_db()
        db = SessionLocal()
        for kw, results in all_results.items():
            keyword_entry = db.query(Keyword).filter(Keyword.keyword == kw).first()
            if not keyword_entry:
                keyword_entry = Keyword(keyword=kw, search_volume=len(results))
                db.add(keyword_entry)
            else:
                keyword_entry.search_volume = len(results)
            keyword_entry.updated_at = __import__("datetime").datetime.now()
        db.commit()
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
