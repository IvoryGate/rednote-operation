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
                    PublishQueue.scheduled_at <= now,
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
                    "tags": json.loads(item.tags) if item.tags else [],
                    "images": json.loads(item.images) if item.images else [],
                }
                success = _publish_via_browser(draft_data, account, dry_run=False)
                if success:
                    item.status = "published"
                    item.published_at = now
                else:
                    item.retry_count = (item.retry_count or 0) + 1
                    if item.retry_count >= 3:
                        item.status = "failed"
                        item.error_message = "Max retries reached"
                    else:
                        item.scheduled_at = datetime.fromtimestamp(now.timestamp() + 300)
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
        from src.core.content_pipeline import build_publish_draft

        # Accept both finalized drafts and AI-filled briefs.
        normalized = build_publish_draft(draft_data)
        entry = PublishQueue(
            account_id=1,
            title=normalized.get("title", ""),
            content=normalized.get("content", ""),
            images=json.dumps(normalized["images"], ensure_ascii=False)
            if normalized.get("images")
            else None,
            tags=json.dumps(normalized["tags"], ensure_ascii=False)
            if normalized.get("tags")
            else None,
            scheduled_at=datetime.fromisoformat(publish_time),
            status="pending",
        )
        db.add(entry)
        db.commit()
        click.echo(f"Scheduled: {entry.title} at {publish_time} (id: {entry.id})")
        db.close()


if __name__ == "__main__":
    main()
