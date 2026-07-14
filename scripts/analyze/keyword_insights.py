"""Extract and analyze keyword/hashtag insights."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from src.core.db import SessionLocal, init_db
from src.core.metrics import extract_tags, tag_insights
from src.models import Keyword, Note


def _notes_from_db() -> list[dict[str, Any]]:
    init_db()
    db = SessionLocal()
    try:
        rows = db.query(Note).all()
        return [
            {
                "title": r.title,
                "content": r.content,
                "tags": r.tags,
                "like_count": r.like_count,
            }
            for r in rows
        ]
    finally:
        db.close()


@click.command()
@click.option("--input", "-i", type=click.Path(exists=True), help="Input JSON file")
@click.option("--from-db", is_flag=True, help="Read from database")
@click.option("--top", default=50, show_default=True, help="Top N keywords")
@click.option("--output", "-o", type=click.Path(), help="Output report file")
@click.option("--update-db", is_flag=True, help="Update keyword trends in DB")
def main(  # type: ignore[no-untyped-def]
    input, from_db, top, output, update_db
) -> None:
    """Extract and analyze keyword/hashtag insights."""
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
        notes = _notes_from_db()
    else:
        click.echo("Provide --input or --from-db")
        return

    ranked = tag_insights(notes, top=top)
    all_tag_mentions = sum(len(extract_tags(n)) for n in notes)

    report_lines = [
        "# Keyword & Hashtag Insights\n",
        f"Notes scanned: {len(notes)}",
        f"Tag mentions: {all_tag_mentions}",
        f"Unique tags (top window): {len(ranked)}\n",
        f"## Top {top} Tags\n",
        "| Rank | Tag | Mentions | Avg likes |",
        "|---:|---|---:|---:|",
    ]
    for i, row in enumerate(ranked, 1):
        report_lines.append(f"| {i} | #{row['tag']} | {row['mentions']} | {row['avg_likes']:.1f} |")

    if update_db:
        init_db()
        db = SessionLocal()
        try:
            for row in ranked:
                existing = db.query(Keyword).filter(Keyword.keyword == row["tag"]).first()
                if existing:
                    existing.search_volume = row["mentions"]
                else:
                    db.add(Keyword(keyword=row["tag"], search_volume=row["mentions"]))
            db.commit()
            click.echo(f"Updated {len(ranked)} keywords in DB")
        finally:
            db.close()

    report = "\n".join(report_lines)

    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(report)
        click.echo(f"Report saved to {path}")
    else:
        click.echo(report)


if __name__ == "__main__":
    main()
