# mypy: ignore-errors
import click

from src.core.db import SessionLocal, init_db
from src.models import PublishQueue


@click.group()
def cli():
    """Manage publishing queue."""
    pass


@cli.command()
@click.option("--status", "-s", default="pending", help="Filter by status")
@click.option("--limit", "-n", default=20, help="Max items to show")
def list(status, limit):
    """List queue items."""
    init_db()
    db = SessionLocal()
    items = (
        db.query(PublishQueue)
        .filter(PublishQueue.status == status)
        .order_by(PublishQueue.scheduled_for.asc())
        .limit(limit)
        .all()
    )
    if not items:
        click.echo("No items in queue")
        return
    click.echo(f"\nQueue items (status: {status}):")
    click.echo(f"{'ID':>4} {'Title':<40} {'Scheduled':<20} {'Status':<12}")
    click.echo("-" * 80)
    for item in items:
        sched = item.scheduled_for.strftime("%Y-%m-%d %H:%M") if item.scheduled_for else "N/A"
        click.echo(f"{item.id:>4} {item.title or 'Untitled':<40} {sched:<20} {item.status:<12}")
    db.close()


@cli.command()
@click.argument("item_id", type=int)
def remove(item_id):
    """Remove item from queue."""
    init_db()
    db = SessionLocal()
    item = db.query(PublishQueue).filter(PublishQueue.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
        click.echo(f"Removed item {item_id}")
    else:
        click.echo(f"Item {item_id} not found")
    db.close()


@cli.command()
@click.argument("item_id", type=int)
def retry(item_id):
    """Retry failed publish."""
    init_db()
    db = SessionLocal()
    item = db.query(PublishQueue).filter(PublishQueue.id == item_id).first()
    if item and item.status == "failed":
        item.status = "pending"
        item.retry_count = 0
        item.error_message = None
        db.commit()
        click.echo(f"Item {item_id} reset to pending for retry")
    else:
        click.echo(f"Item {item_id} not found or not in failed state")
    db.close()


if __name__ == "__main__":
    cli()
