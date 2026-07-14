"""Analyze content performance metrics."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import click

from src.core.db import SessionLocal, init_db
from src.core.metrics import (
    collect_rate,
    engagement_rate,
    enrich_note,
    format_rate,
    format_summary_markdown,
    summarize_notes,
)
from src.models import Note


def _notes_from_db(days: int) -> list[dict[str, Any]]:
    init_db()
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=days)
        rows = db.query(Note).filter(Note.published_at >= cutoff).all()
        return [
            {
                "title": r.title,
                "like_count": r.like_count,
                "collect_count": r.collect_count,
                "comment_count": r.comment_count,
                "share_count": r.share_count,
                "view_count": r.view_count,
                "published_at": str(r.published_at) if r.published_at else "",
                "url": r.url,
                "note_id": r.note_id,
            }
            for r in rows
        ]
    finally:
        db.close()


def _sort_key(sort_by: str):  # type: ignore[no-untyped-def]
    if sort_by == "likes":
        return lambda n: n.get("like_count", 0) or 0
    if sort_by == "collects":
        return lambda n: n.get("collect_count", 0) or 0
    if sort_by == "comments":
        return lambda n: n.get("comment_count", 0) or 0
    if sort_by == "engagement":
        return lambda n: engagement_rate(n) or 0.0
    if sort_by == "collect_rate":
        return lambda n: collect_rate(n) or 0.0
    return lambda n: n.get("published_at", "") or ""


@click.command()
@click.option("--input", "-i", type=click.Path(exists=True), help="Input JSON file")
@click.option("--from-db", is_flag=True, help="Read from database")
@click.option("--days", default=30, show_default=True, help="Look back days")
@click.option("--output", "-o", type=click.Path(), help="Output report file")
@click.option("--top", default=20, show_default=True, help="Top N results")
@click.option(
    "--sort-by",
    type=click.Choice(["likes", "collects", "comments", "date", "engagement", "collect_rate"]),
    default="likes",
)
@click.option("--viral-threshold", default=1000, show_default=True, help="Likes threshold for 爆文")
@click.option("--cost", type=float, default=None, help="Total publish cost for CPV")
def main(  # type: ignore[no-untyped-def]
    input, from_db, days, output, top, sort_by, viral_threshold, cost
) -> None:
    """Analyze content performance metrics."""
    notes: list[dict[str, Any]] = []

    if input:
        with open(input) as f:
            loaded = json.load(f)
        if isinstance(loaded, dict) and "notes" in loaded:
            notes = list(loaded["notes"])
        elif isinstance(loaded, list):
            notes = loaded
        else:
            click.echo("Input JSON must be a list of notes or {notes: [...]}")
            return
    elif from_db:
        notes = _notes_from_db(days)
    else:
        click.echo("Provide --input or --from-db")
        return

    if not notes:
        click.echo("No data to analyze")
        return

    summary = summarize_notes(notes, viral_threshold=viral_threshold, cost=cost)
    enriched = [enrich_note(n) for n in notes]
    reverse = sort_by != "date"
    top_notes = sorted(enriched, key=_sort_key(sort_by), reverse=reverse)[:top]

    report = [
        f"# Content Performance Report\nPeriod: last {days} days | Notes: {len(notes)}\n",
        format_summary_markdown(summary),
        f"## Top {top} by {sort_by}\n",
    ]
    for i, n in enumerate(top_notes, 1):
        report.append(
            f"{i}. {n.get('title', 'Untitled')[:50]} | "
            f"❤ {int(n.get('like_count', 0) or 0)} "
            f"🔖 {int(n.get('collect_count', 0) or 0)} "
            f"💬 {int(n.get('comment_count', 0) or 0)} "
            f"| eng {format_rate(n.get('engagement_rate'))} "
            f"| collect {format_rate(n.get('collect_rate'))}"
        )

    if summary.get("notes_with_views", 0) == 0:
        report.append(
            "\n> Note: no `view_count` in dataset — engagement/collect rates are N/A. "
            "Crawl detail pages or enrich JSON to enable rate metrics.\n"
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
