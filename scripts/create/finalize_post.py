"""Finalize an AI-filled brief into a publish-ready draft."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from src.core.content_pipeline import build_publish_draft, extract_post_fields, validate_post
from src.core.db import SessionLocal, init_db
from src.models import ContentCalendar, PublishQueue


def _load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise click.ClickException(f"{path} must contain a JSON object")
    return data


@click.command()
@click.option("--brief", "-b", type=click.Path(exists=True), required=True, help="Filled brief JSON")
@click.option(
    "--images-json",
    type=click.Path(exists=True),
    help="Optional image specs JSON from generate_image.py",
)
@click.option(
    "--image",
    "image_paths",
    multiple=True,
    type=click.Path(),
    help="Local image path (repeatable)",
)
@click.option("--output", "-o", type=click.Path(), help="Write finalized draft JSON")
@click.option("--strict/--no-strict", default=True, help="Fail on quality-gate violations")
@click.option("--require-images", is_flag=True, help="Require 3-9 image paths")
@click.option("--queue", is_flag=True, help="Enqueue to publish_queue")
@click.option("--time", "publish_time", help="Schedule time YYYY-MM-DD HH:MM (with --queue)")
@click.option("--account-id", default=1, show_default=True, help="Account id for queue/calendar")
@click.option("--calendar-id", type=int, default=None, help="Link ContentCalendar id")
@click.option("--update-calendar", is_flag=True, help="Mark linked calendar entry final")
def main(  # type: ignore[no-untyped-def]
    brief,
    images_json,
    image_paths,
    output,
    strict,
    require_images,
    queue,
    publish_time,
    account_id,
    calendar_id,
    update_calendar,
) -> None:
    """Validate a filled brief and emit a publish-ready draft.

    Bridges generate_post (brief) → AI fill → schedule_post / publish_now.
    """
    data = _load_json(Path(brief))

    extra_images = list(image_paths)
    extra_specs: list[Any] | None = None
    if images_json:
        img_doc = _load_json(Path(images_json))
        specs = img_doc.get("image_specs") or img_doc.get("specs") or []
        if isinstance(specs, list):
            extra_specs = specs
        paths = img_doc.get("images") or []
        if isinstance(paths, list):
            extra_images.extend(str(p) for p in paths)

    fields = extract_post_fields(data)
    if extra_images:
        fields["images"] = extra_images
    if extra_specs is not None:
        fields["image_specs"] = extra_specs

    issues = validate_post(fields, require_images=require_images)
    if issues:
        click.echo("Quality check:")
        for issue in issues:
            click.echo(f"  - {issue}")
        if strict:
            raise click.ClickException(f"{len(issues)} quality issue(s); use --no-strict to continue")
        click.echo("Continuing with --no-strict")
    else:
        click.echo("Quality check: OK")

    draft = build_publish_draft(
        data,
        images=fields["images"],
        image_specs=fields.get("image_specs"),
    )

    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)
        click.echo(f"Final draft written: {path}")
    else:
        click.echo(json.dumps(draft, ensure_ascii=False, indent=2))

    if queue:
        from datetime import datetime

        if not publish_time:
            raise click.ClickException("--time is required with --queue")
        init_db()
        db = SessionLocal()
        try:
            entry = PublishQueue(
                account_id=account_id,
                calendar_id=calendar_id,
                title=draft["title"],
                content=draft["content"],
                images=json.dumps(draft["images"], ensure_ascii=False) if draft["images"] else None,
                tags=json.dumps(draft["tags"], ensure_ascii=False) if draft["tags"] else None,
                scheduled_at=datetime.fromisoformat(publish_time),
                status="pending",
            )
            db.add(entry)
            if update_calendar and calendar_id:
                cal = db.query(ContentCalendar).filter(ContentCalendar.id == calendar_id).first()
                if cal:
                    cal.status = "final"
                    cal.title = draft["title"]
                    cal.content = draft["content"]
                    cal.tags = ",".join(draft["tags"])
            db.commit()
            click.echo(f"Queued publish id={entry.id} at {publish_time}")
        finally:
            db.close()


if __name__ == "__main__":
    main()
