import json
from datetime import datetime
from pathlib import Path

import click

from src.core.db import SessionLocal, init_db
from src.models import ContentCalendar


def _list_templates() -> dict[str, list[str]]:
    templates_dir = Path("knowledge/templates/post_templates")
    result: dict[str, list[str]] = {}
    if not templates_dir.exists():
        return result
    for f in sorted(templates_dir.glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        subtemplates = [line[2:] for line in lines if line.startswith("## ")]
        result[f.stem] = subtemplates
    return result


def _load_template(category: str) -> str:
    path = Path(f"knowledge/templates/post_templates/{category}.md")
    if not path.exists():
        raise click.ClickException(f"Template not found: {category}")
    return path.read_text(encoding="utf-8")


def _load_prompts() -> str:
    path = Path("knowledge/prompts/copywriting_prompts.md")
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _extract_section(text: str, section_name: str) -> str:
    """Extract a ## section block from template markdown."""
    lines = text.splitlines()
    start = None
    depth = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("## ") and section_name in line:
            start = i
            break
    if start is None:
        return ""
    result = []
    for line in lines[start + 1 :]:
        if line.strip().startswith("## ") and depth == 0:
            break
        if line.strip().startswith("## "):
            depth -= 1
            if depth < 0:
                break
        if line.strip().startswith("### "):
            depth += 1
        result.append(line)
    return "\n".join(result).strip()


@click.command()
@click.option("--topic", "-t", required=True, help="Post topic")
@click.option("--category", "-c", required=True, help="Category (food/travel/digital)")
@click.option("--template", help="Sub-template name (e.g. '探店打卡')")
@click.option("--output", "-o", type=click.Path(), help="Output brief JSON file")
@click.option("--db", "to_db", is_flag=True, help="Save draft to database")
@click.option("--list-templates", is_flag=True, help="List available templates")
def main(topic, category, template, output, to_db, list_templates):  # type: ignore[no-untyped-def]
    """Generate a post creation brief from templates and prompts.

    Produces a structured JSON file that the AI agent uses to generate
    the final post content (title, body, tags, image specs).
    """
    if list_templates:
        templates = _list_templates()
        if not templates:
            click.echo("No templates found")
            return
        for cat, subs in templates.items():
            click.echo(f"\n[{cat}]")
            for s in subs:
                click.echo(f"  - {s}")
        return

    template_text = _load_template(category)
    prompts_text = _load_prompts()

    brief = {
        "meta": {
            "topic": topic,
            "category": category,
            "template": template or "",
            "created_at": datetime.now().isoformat(),
        },
        "template": _extract_section(template_text, template) if template else template_text,
        "copywriting_prompts": prompts_text,
        "generated": {
            "title": "",
            "body": "",
            "tags": [],
            "image_specs": [],
        },
    }

    if to_db:
        init_db()
        db = SessionLocal()
        entry = ContentCalendar(
            account_id=1,
            title=topic,
            content=json.dumps(brief, ensure_ascii=False),
            category=category,
            status="brief",
            tags="",
        )
        db.add(entry)
        db.commit()
        db.close()
        click.echo(f"Brief saved to DB (id: {entry.id})")

    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(brief, f, ensure_ascii=False, indent=2)
        click.echo(f"Brief saved to {path}")
    else:
        click.echo(json.dumps(brief, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
