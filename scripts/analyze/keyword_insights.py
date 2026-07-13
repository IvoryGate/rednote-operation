# mypy: ignore-errors
import json
from collections import Counter
from pathlib import Path

import click

from src.core.db import SessionLocal, init_db
from src.models import Keyword, Note


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
    notes = []

    if input:
        with open(input) as f:
            notes = json.load(f)
    elif from_db:
        init_db()
        db = SessionLocal()
        results = db.query(Note).filter(Note.tags.isnot(None)).all()
        for r in results:
            notes.append({"title": r.title, "tags": r.tags, "like_count": r.like_count})
        db.close()
    else:
        click.echo("Provide --input or --from-db")
        return

    all_tags = []
    for n in notes:
        tags = n.get("tags", "") or ""
        if isinstance(tags, str):
            all_tags.extend(t.strip() for t in tags.split(",") if t.strip())

    tag_counts = Counter(all_tags)
    top_tags = tag_counts.most_common(top)

    report_lines = ["# Keyword & Hashtag Insights\n"]
    report_lines.append(f"Total tags found: {len(all_tags)}")
    report_lines.append(f"Unique tags: {len(tag_counts)}\n")
    report_lines.append(f"## Top {top} Tags\n")
    for i, (tag, count) in enumerate(top_tags, 1):
        report_lines.append(f"{i}. #{tag} — {count} mentions")

    if update_db:
        init_db()
        db = SessionLocal()
        for tag, count in top_tags:
            existing = db.query(Keyword).filter(Keyword.keyword == tag).first()
            if existing:
                existing.search_volume = count
            else:
                db.add(Keyword(keyword=tag, search_volume=count))
        db.commit()
        db.close()
        click.echo(f"Updated {len(top_tags)} keywords in DB")

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
