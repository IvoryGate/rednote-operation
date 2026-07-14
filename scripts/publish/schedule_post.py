# mypy: ignore-errors


import json
import time
from datetime import datetime

import click

from src.core.db import SessionLocal, init_db
from src.models import PublishQueue


@click.command()
@click.option("--add", is_flag=True, help="Add post to schedule")
@click.option("--draft", type=click.Path(exists=True), help="Draft JSON file")
@click.option("--time", "publish_time", help="Publish time (YYYY-MM-DD HH:MM)")
@click.option("--account", default="main", help="Account name to publish from")
@click.option("--daemon", is_flag=True, help="Run as daemon, auto-publish at scheduled times")
@click.option("--interval", default=60, help="Daemon check interval (seconds)")
def main(add, draft, publish_time, account, daemon, interval) -> None:
    """Schedule posts for publishing."""
    init_db()

    if daemon:
        click.echo(f"Daemon mode: checking every {interval}s for account '{account}'")
        while True:
            db = SessionLocal()
            now = datetime.now()
            pending = (
                db.query(PublishQueue)
                .filter(
                    PublishQueue.status == "pending",
                    PublishQueue.scheduled_for <= now,
                )
                .limit(5)
                .all()
            )
            for item in pending:
                click.echo(f"Publishing queue item {item.id}: {item.title}")
                # Delegate to publish_now logic
                from scripts.publish.publish_now import _publish_via_browser

                draft_data = {
                    "title": item.title or "",
                    "content": item.content or "",
                    "tags": [],
                }
                success = _publish_via_browser(draft_data, account)
                if success:
                    item.status = "published"
                    item.published_at = now
                else:
                    item.retry_count = (item.retry_count or 0) + 1
                    if item.retry_count >= 3:
                        item.status = "failed"
                        item.error_message = "Max retries reached"
                    else:
                        item.scheduled_for = datetime.fromtimestamp(now.timestamp() + 300)
            if pending:
                db.commit()
                click.echo(f"Processed {len(pending)} items")
            db.close()
            time.sleep(interval)

    if add:
        if not draft or not publish_time:
            click.echo("--draft and --time are required with --add")
            return
        db = SessionLocal()
        with open(draft) as f:
            draft_data = json.load(f)
        entry = PublishQueue(
            account_id=1,
            title=draft_data.get("title", ""),
            content=draft_data.get("content", ""),
            scheduled_for=datetime.fromisoformat(publish_time),
            status="pending",
        )
        db.add(entry)
        db.commit()
        click.echo(f"Scheduled: {entry.title} at {publish_time} (id: {entry.id})")
        db.close()


if __name__ == "__main__":
    main()
