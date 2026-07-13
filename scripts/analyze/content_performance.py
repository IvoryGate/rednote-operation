# mypy: ignore-errors
import json
from datetime import datetime, timedelta
from pathlib import Path

import click

from src.core.db import SessionLocal, init_db
from src.models import Note


@click.command()
@click.option("--input", "-i", type=click.Path(exists=True), help="Input JSON file")
@click.option("--from-db", is_flag=True, help="Read from database")
@click.option("--days", default=30, show_default=True, help="Look back days")
@click.option("--output", "-o", type=click.Path(), help="Output report file")
@click.option("--top", default=20, show_default=True, help="Top N results")
@click.option(
    "--sort-by", type=click.Choice(["likes", "collects", "comments", "date"]), default="likes"
)
def main(  # type: ignore[no-untyped-def]
    input, from_db, days, output, top, sort_by
) -> None:
    """Analyze content performance metrics."""
    notes = []

    if input:
        with open(input) as f:
            notes = json.load(f)
    elif from_db:
        init_db()
        db = SessionLocal()
        cutoff = datetime.now() - timedelta(days=days)
        results = db.query(Note).filter(Note.published_at >= cutoff).all()
        for r in results:
            notes.append(
                {
                    "title": r.title,
                    "like_count": r.like_count,
                    "collect_count": r.collect_count,
                    "comment_count": r.comment_count,
                    "share_count": r.share_count,
                    "published_at": str(r.published_at) if r.published_at else "",
                }
            )
        db.close()
    else:
        click.echo("Provide --input or --from-db")
        return

    if not notes:
        click.echo("No data to analyze")
        return

    if sort_by == "likes":

        def key_func(n):
            return n.get("like_count", 0)
    elif sort_by == "collects":

        def key_func(n):
            return n.get("collect_count", 0)
    elif sort_by == "comments":

        def key_func(n):
            return n.get("comment_count", 0)
    else:

        def key_func(n):
            return n.get("published_at", "")

    sorted_notes = sorted(notes, key=key_func, reverse=(sort_by != "date"))
    top_notes = sorted_notes[:top]

    avg_likes = sum(n.get("like_count", 0) for n in notes) / len(notes)
    avg_collects = sum(n.get("collect_count", 0) for n in notes) / len(notes)

    report = [
        f"# Content Performance Report\nPeriod: last {days} days | Notes: {len(notes)}\n",
        f"## Summary\n- Avg likes: {avg_likes:.1f}\n- Avg collects: {avg_collects:.1f}\n",
        f"## Top {top} by {sort_by}\n",
    ]
    for i, n in enumerate(top_notes, 1):
        report.append(
            f"{i}. {n.get('title', 'Untitled')[:50]} | "
            f"❤ {n.get('like_count', 0)} "
            f"🔖 {n.get('collect_count', 0)} "
            f"💬 {n.get('comment_count', 0)}"
        )

    result = "\n".join(report)

    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(result)
        click.echo(f"Report saved to {path}")
    else:
        click.echo(result)


if __name__ == "__main__":
    main()
