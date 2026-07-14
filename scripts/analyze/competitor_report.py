"""Generate competitor analysis report with engagement metrics."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import click

from src.core.db import SessionLocal, init_db
from src.core.metrics import format_summary_markdown, summarize_notes
from src.models import Competitor, Note


def _notes_for_competitor(db: Any, competitor: Competitor, days: int) -> list[dict[str, Any]]:
    cutoff = datetime.now() - timedelta(days=days)
    rows = (
        db.query(Note)
        .filter(Note.account_id == competitor.id)
        .filter((Note.published_at.is_(None)) | (Note.published_at >= cutoff))
        .all()
    )
    return [
        {
            "title": r.title,
            "like_count": r.like_count,
            "collect_count": r.collect_count,
            "comment_count": r.comment_count,
            "share_count": r.share_count,
            "view_count": r.view_count,
            "published_at": str(r.published_at) if r.published_at else "",
        }
        for r in rows
    ]


@click.command()
@click.option("--competitor", "-c", multiple=True, help="Competitor name(s)")
@click.option("--compare", is_flag=True, help="Compare all active competitors")
@click.option("--days", default=30, show_default=True, help="Look back days for note metrics")
@click.option("--output", "-o", type=click.Path(), help="Output report file")
@click.option("--viral-threshold", default=1000, show_default=True)
def main(  # type: ignore[no-untyped-def]
    competitor, compare, days, output, viral_threshold
) -> None:
    """Generate competitor analysis report."""
    init_db()
    db = SessionLocal()

    try:
        competitors: list[Competitor] = []
        if competitor:
            competitors = (
                db.query(Competitor).filter(Competitor.competitor_name.in_(competitor)).all()
            )
        elif compare:
            competitors = db.query(Competitor).filter(Competitor.is_active).all()

        if not competitors:
            click.echo("No competitors found. Add with monitor_account.py --name --user-id")
            return

        report_lines = [
            f"# Competitor Analysis Report\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Window: last {days} days\n",
        ]

        comparison_rows: list[tuple[str, dict[str, Any]]] = []

        for c in competitors:
            notes = _notes_for_competitor(db, c, days)
            summary = summarize_notes(notes, viral_threshold=viral_threshold)
            comparison_rows.append((c.competitor_name, summary))

            report_lines.extend(
                [
                    f"\n## {c.competitor_name}",
                    f"- Followers: {c.followers}",
                    f"- Profile notes_count: {c.notes_count}",
                    f"- Stored avg likes/comments: {c.avg_likes:.1f} / {c.avg_comments:.1f}",
                    f"- Category: {c.category or 'N/A'}",
                    format_summary_markdown(
                        summary, heading=f"### Note metrics (last {days}d, n={len(notes)})"
                    ),
                ]
            )

        if len(comparison_rows) > 1:
            report_lines.append("\n## Comparison\n")
            report_lines.append(
                "| Competitor | Notes | Median likes | Eng rate | Collect rate | Viral % |"
            )
            report_lines.append("|---|---:|---:|---:|---:|---:|")
            for name, s in comparison_rows:
                eng = (
                    f"{s['avg_engagement_rate'] * 100:.2f}%"
                    if s.get("avg_engagement_rate") is not None
                    else "N/A"
                )
                col = (
                    f"{s['avg_collect_rate'] * 100:.2f}%"
                    if s.get("avg_collect_rate") is not None
                    else "N/A"
                )
                report_lines.append(
                    f"| {name} | {s['note_count']} | {s['median_likes']:.1f} | "
                    f"{eng} | {col} | {s['viral_rate'] * 100:.1f}% |"
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
    finally:
        db.close()


if __name__ == "__main__":
    main()
