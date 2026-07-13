# mypy: ignore-errors
import json
from datetime import datetime
from pathlib import Path

import click

from src.core.db import SessionLocal, init_db
from src.models import ContentCalendar


@click.command()
@click.option("--title", "-t", help="Post title")
@click.option("--content", "-c", help="Post body content")
@click.option("--template", help="Template name (food/travel/digital)")
@click.option("--tags", help="Comma-separated hashtags")
@click.option("--images", help="Comma-separated image paths")
@click.option("--category", help="Content category")
@click.option("--output", "-o", type=click.Path(), help="Output draft file")
@click.option("--db", "to_db", is_flag=True, help="Save to database")
@click.option("--list-templates", is_flag=True, help="List available templates")
def main(  # type: ignore[no-untyped-def]
    title, content, template, tags, images, category, output, to_db, list_templates
) -> None:
    """Generate and save AI post content."""
    if list_templates:
        templates_dir = Path("knowledge/templates/post_templates")
        if templates_dir.exists():
            for f in sorted(templates_dir.glob("*.md")):
                click.echo(
                    f"  {f.stem}: {f.read_text().split(chr(10))[0] if f.read_text() else 'empty'}"
                )
        else:
            click.echo("No templates found")
        return

    if not title:
        click.echo("--title is required")
        return

    draft = {
        "title": title,
        "content": content or "",
        "template": template or "",
        "tags": [t.strip() for t in (tags or "").split(",") if t.strip()],
        "images": [i.strip() for i in (images or "").split(",") if i.strip()],
        "category": category or template or "",
        "created_at": datetime.now().isoformat(),
    }

    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)
        click.echo(f"Draft saved to {path}")

    if to_db:
        init_db()
        db = SessionLocal()
        entry = ContentCalendar(
            account_id=1,
            title=title,
            content=content,
            category=category or template or "",
            status="draft",
            tags=tags,
        )
        db.add(entry)
        db.commit()
        db.close()
        click.echo(f"Draft saved to DB (id: {entry.id})")

    click.echo(f"Title: {title}")
    if content:
        click.echo(f"Content: {len(content)} chars")


if __name__ == "__main__":
    main()
