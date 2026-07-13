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
    db = SessionLocal()

    if daemon:
        click.echo(f"Daemon mode: checking every {interval}s")
        while True:
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
                click.echo(f"Publishing queue item {item.id}...")
                item.status = "published"
                item.published_at = now
            if pending:
                db.commit()
                click.echo(f"Published {len(pending)} items")
            db.close()
            time.sleep(interval)
            db = SessionLocal()

    if add:
        if not draft or not publish_time:
            click.echo("--draft and --time are required with --add")
            return
        with open(draft) as f:
            draft_data = json.load(f)
        entry = PublishQueue(
            account_id=1,
            title=draft_data.get("title", ""),
            scheduled_for=datetime.fromisoformat(publish_time),
            status="pending",
        )
        db.add(entry)
        db.commit()
        click.echo(f"Scheduled: {entry.title} at {publish_time} (id: {entry.id})")

    db.close()


if __name__ == "__main__":
    main()
