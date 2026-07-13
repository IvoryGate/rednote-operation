import json
from datetime import datetime, timedelta
from pathlib import Path

import click

from src.core.browser import Browser
from src.core.db import SessionLocal, init_db
from src.models import Competitor, Note


def extract_metrics(page: object) -> dict:
    # TODO: extract follower count, note count from profile page
    return {"followers": 0, "notes_count": 0}


def extract_notes(page: object) -> list[dict]:
    # TODO: extract note list items from profile page
    return []


@click.command()
@click.option("--name", "-n", help="Competitor display name")
@click.option("--user-id", "-u", help="Xiaohongshu user ID")
@click.option("--category", "-c", help="Category")
@click.option("--update", is_flag=True, help="Update competitor data")
@click.option("--list", "list_only", is_flag=True, help="List monitored accounts")
@click.option("--all", "update_all", is_flag=True, help="Update all accounts")
@click.option("--days", default=30, show_default=True, help="Look back days")
@click.option("--output", "-o", type=click.Path(), help="Output report path")
@click.option("--headless", is_flag=True, help="Run browser headless")
@click.option("--account", "session_account", default="main", help="Session account name")
def main(  # type: ignore[no-untyped-def]
    name, user_id, category, update, list_only, update_all, days, output, headless, session_account
) -> None:
    """Monitor competitor accounts on Xiaohongshu."""
    init_db()
    db = SessionLocal()

    if list_only:
        competitors = db.query(Competitor).all()
        for c in competitors:
            click.echo(
                f"{c.id}: {c.competitor_name} "
                f"(followers: {c.followers}, "
                f"category: {c.category or '-'})"
            )
        db.close()
        return

    if name and user_id and not update:
        competitor = Competitor(
            account_id=1,
            competitor_name=name,
            competitor_url=f"https://www.xiaohongshu.com/user/profile/{user_id}",
            category=category,
        )
        db.add(competitor)
        db.commit()
        click.echo(f"Added competitor: {name}")
        db.close()
        return

    def collect_data(competitor: Competitor) -> dict:
        url = (
            competitor.competitor_url
            or f"https://www.xiaohongshu.com/user/profile/{competitor.competitor_name}"
        )
        with Browser() as browser:
            browser.start()
            ctx = browser.session_context(session_account)
            page = ctx.new_page()
            page.goto(url)

            metrics = extract_metrics(page)
            notes_data = extract_notes(page)
            notes_data = notes_data[:50]

        cutoff = datetime.now() - timedelta(days=days)
        new_notes = 0
        for item in notes_data:
            existing = db.query(Note).filter(Note.note_id == item.get("note_id")).first()
            if not existing:
                note = Note(
                    account_id=competitor.id,
                    note_id=item["note_id"],
                    title=item.get("title"),
                    like_count=item.get("like_count", 0),
                    collect_count=item.get("collect_count", 0),
                    comment_count=item.get("comment_count", 0),
                    share_count=item.get("share_count", 0),
                    url=item.get("url"),
                    published_at=item.get("published_at"),
                )
                db.add(note)
                new_notes += 1

        competitor.followers = metrics.get("followers", competitor.followers)
        competitor.notes_count = metrics.get("notes_count", competitor.notes_count)

        recent_notes = (
            db.query(Note)
            .filter(Note.account_id == competitor.id, Note.published_at >= cutoff)
            .all()
        )
        if recent_notes:
            competitor.avg_likes = sum(n.like_count for n in recent_notes) / len(recent_notes)
            competitor.avg_comments = sum(n.comment_count for n in recent_notes) / len(recent_notes)

        competitor.updated_at = datetime.now()
        db.commit()

        return {
            "id": competitor.id,
            "name": competitor.competitor_name,
            "followers": competitor.followers,
            "notes_count": competitor.notes_count,
            "avg_likes": competitor.avg_likes,
            "avg_comments": competitor.avg_comments,
            "new_notes": new_notes,
            "updated_at": competitor.updated_at.isoformat(),
        }

    results = []

    if update and name:
        competitor = db.query(Competitor).filter(Competitor.competitor_name == name).first()
        if not competitor:
            click.echo(f"Competitor '{name}' not found")
            db.close()
            return
        result = collect_data(competitor)
        results.append(result)
        click.echo(f"Updated: {competitor.competitor_name} (followers: {competitor.followers})")

    if update_all:
        competitors = db.query(Competitor).filter(Competitor.is_active).all()
        for competitor in competitors:
            result = collect_data(competitor)
            results.append(result)
            click.echo(f"Updated: {competitor.competitor_name} (followers: {competitor.followers})")
        click.echo(f"Updated {len(competitors)} competitors")

    if output and results:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        click.echo(f"Report saved to {output}")

    db.close()


if __name__ == "__main__":
    main()
