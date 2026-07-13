from datetime import datetime
from pathlib import Path

import click

from src.core.db import SessionLocal, init_db
from src.models import Competitor


@click.command()
@click.option("--competitor", "-c", multiple=True, help="Competitor name(s)")
@click.option("--compare", is_flag=True, help="Compare all active competitors")
@click.option("--days", default=30, show_default=True, help="Look back days")
@click.option("--output", "-o", type=click.Path(), help="Output report file")
def main(  # type: ignore[no-untyped-def]
    competitor, compare, days, output
) -> None:
    """Generate competitor analysis report."""
    init_db()
    db = SessionLocal()

    competitors = []
    if competitor:
        competitors = db.query(Competitor).filter(Competitor.competitor_name.in_(competitor)).all()
    elif compare:
        competitors = db.query(Competitor).filter(Competitor.is_active).all()

    if not competitors:
        click.echo("No competitors found. Add with monitor_account.py --name --user-id")
        return

    report_lines = [
        f"# Competitor Analysis Report\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    ]
    for c in competitors:
        report_lines.extend(
            [
                f"\n## {c.competitor_name}",
                f"- Followers: {c.followers}",
                f"- Notes: {c.notes_count}",
                f"- Avg Likes: {c.avg_likes:.1f}",
                f"- Avg Comments: {c.avg_comments:.1f}",
                f"- Category: {c.category or 'N/A'}",
            ]
        )

    report = "\n".join(report_lines)

    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(report)
        click.echo(f"Report saved to {path}")
    else:
        click.echo(report)

    db.close()


if __name__ == "__main__":
    main()
