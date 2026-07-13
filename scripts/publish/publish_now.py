# mypy: ignore-errors
import json

import click

from src.core.browser import Browser
from src.core.db import SessionLocal, init_db
from src.models import PublishQueue


@click.command()
@click.option("--draft", type=click.Path(exists=True), help="Draft JSON file to publish")
@click.option("--queue-id", type=int, help="Queue item ID to publish")
@click.option("--account", default="main", help="Account name")
@click.option("--headless", is_flag=True, help="Run browser headless")
def main(draft, queue_id, account, headless) -> None:
    """Publish a post to Xiaohongshu immediately."""
    init_db()
    db = SessionLocal()

    if queue_id:
        item = db.query(PublishQueue).filter(PublishQueue.id == queue_id).first()
        if not item:
            click.echo(f"Queue item {queue_id} not found")
            return
        draft_data = {"title": item.title, "content": item.content or ""}
        click.echo(f"Publishing from queue: {item.title}")
    elif draft:
        with open(draft) as f:
            draft_data = json.load(f)
        click.echo(f"Publishing draft: {draft_data.get('title', 'Untitled')}")
    else:
        click.echo("Provide --draft or --queue-id")
        return

    # TODO: Use Browser to navigate to Xiaohongshu publish page
    # and fill in the form with draft_data
    with Browser() as browser:
        browser.start()
        browser.page()
        # page.goto("https://creator.xiaohongshu.com/publish")
        # ... form filling logic ...
        click.echo("Publishing via browser automation (TODO)")

    if queue_id:
        import datetime

        item = db.query(PublishQueue).filter(PublishQueue.id == queue_id).first()
        if item:
            item.status = "published"
            item.published_at = datetime.datetime.now()
            db.commit()
            click.echo(f"Queue item {queue_id} marked as published")

    db.close()


if __name__ == "__main__":
    main()
