import json
from pathlib import Path

import click

from src.core.browser import Browser
from src.core.db import SessionLocal, init_db
from src.models import Note


def extract_note_data(page: object) -> dict:
    # TODO: extract note data from Xiaohongshu page
    return {}


def extract_notes_from_list(page: object) -> list[dict]:
    # TODO: extract note list from profile/search page
    return []


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

    with Browser() as browser:
        browser.start()
        ctx = browser.session_context(session_account)
        page = ctx.new_page()

        if url:
            page.goto(url)
            data = extract_note_data(page)
            if data:
                results.append(data)
        elif user_id:
            page.goto(f"https://www.xiaohongshu.com/user/profile/{user_id}")
            results = extract_notes_from_list(page)[:count]
        elif query:
            page.goto(f"https://www.xiaohongshu.com/search_result?keyword={query}")
            results = extract_notes_from_list(page)[:count]

    if to_db and results:
        init_db()
        db = SessionLocal()
        for item in results:
            note = Note(**item)
            db.add(note)
        db.commit()
        db.close()

    if output and results:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    click.echo(f"Collected {len(results)} notes")


if __name__ == "__main__":
    main()
