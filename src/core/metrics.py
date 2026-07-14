"""Content performance metrics used by analyze scripts and skills docs."""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

DEFAULT_VIRAL_LIKES = 1000


def _num(note: dict[str, Any], *keys: str) -> float:
    for key in keys:
        if key in note and note[key] is not None:
            try:
                return float(note[key])
            except (TypeError, ValueError):
                continue
    return 0.0


def likes(note: dict[str, Any]) -> float:
    return _num(note, "like_count", "likes")


def collects(note: dict[str, Any]) -> float:
    return _num(note, "collect_count", "collects")


def comments(note: dict[str, Any]) -> float:
    return _num(note, "comment_count", "comments")


def shares(note: dict[str, Any]) -> float:
    return _num(note, "share_count", "shares")


def views(note: dict[str, Any]) -> float:
    return _num(note, "view_count", "views", "exposure")


def interactions(note: dict[str, Any]) -> float:
    return likes(note) + collects(note) + comments(note)


def engagement_rate(note: dict[str, Any]) -> float | None:
    """(likes + collects + comments) / views. None when exposure is unknown."""
    v = views(note)
    if v <= 0:
        return None
    return interactions(note) / v


def collect_rate(note: dict[str, Any]) -> float | None:
    """collects / views. None when exposure is unknown."""
    v = views(note)
    if v <= 0:
        return None
    return collects(note) / v


def median_of(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(statistics.median(values))


def mean_of(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(statistics.fmean(values))


def viral_rate(notes: list[dict[str, Any]], threshold: int = DEFAULT_VIRAL_LIKES) -> float:
    """Share of notes with likes above *threshold* (爆文率)."""
    if not notes:
        return 0.0
    viral = sum(1 for n in notes if likes(n) >= threshold)
    return viral / len(notes)


def cpv(notes: list[dict[str, Any]], cost: float) -> float | None:
    """Combined interactions per unit publish cost. None when cost <= 0."""
    if cost <= 0 or not notes:
        return None
    total = sum(interactions(n) for n in notes)
    return total / cost


def summarize_notes(
    notes: list[dict[str, Any]],
    *,
    viral_threshold: int = DEFAULT_VIRAL_LIKES,
    cost: float | None = None,
) -> dict[str, Any]:
    """Aggregate metrics for a note list."""
    like_vals = [likes(n) for n in notes]
    collect_vals = [collects(n) for n in notes]
    comment_vals = [comments(n) for n in notes]
    view_vals = [views(n) for n in notes if views(n) > 0]

    eng = [engagement_rate(n) for n in notes]
    eng_known = [x for x in eng if x is not None]
    col = [collect_rate(n) for n in notes]
    col_known = [x for x in col if x is not None]

    summary: dict[str, Any] = {
        "note_count": len(notes),
        "avg_likes": mean_of(like_vals),
        "median_likes": median_of(like_vals),
        "avg_collects": mean_of(collect_vals),
        "median_collects": median_of(collect_vals),
        "avg_comments": mean_of(comment_vals),
        "median_comments": median_of(comment_vals),
        "avg_views": mean_of(view_vals) if view_vals else None,
        "avg_engagement_rate": mean_of(eng_known) if eng_known else None,
        "avg_collect_rate": mean_of(col_known) if col_known else None,
        "notes_with_views": len(view_vals),
        "viral_threshold": viral_threshold,
        "viral_rate": viral_rate(notes, viral_threshold),
        "viral_count": sum(1 for n in notes if likes(n) >= viral_threshold),
    }
    if cost is not None:
        summary["cost"] = cost
        summary["cpv"] = cpv(notes, cost)
    return summary


def enrich_note(note: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy with computed rate fields."""
    out = dict(note)
    out["interactions"] = interactions(note)
    out["engagement_rate"] = engagement_rate(note)
    out["collect_rate"] = collect_rate(note)
    return out


def extract_tags(note: dict[str, Any]) -> list[str]:
    """Pull tags from ``tags`` field and inline #hashtags in title/content."""
    found: list[str] = []
    raw = note.get("tags")
    if isinstance(raw, list):
        found.extend(str(t).strip().lstrip("#") for t in raw if str(t).strip())
    elif isinstance(raw, str) and raw.strip():
        # comma / whitespace / # separated
        for part in raw.replace("#", " ").replace(",", " ").split():
            if part.strip():
                found.append(part.strip())

    for field in ("title", "content", "body"):
        text = note.get(field) or ""
        if not isinstance(text, str):
            continue
        for token in text.split():
            if token.startswith("#") and len(token) > 1:
                found.append(token.lstrip("#").strip(".,!?;:"))

    # de-dupe preserving order (case-sensitive for CN tags)
    seen: set[str] = set()
    ordered: list[str] = []
    for tag in found:
        if tag and tag not in seen:
            seen.add(tag)
            ordered.append(tag)
    return ordered


def tag_insights(
    notes: list[dict[str, Any]],
    *,
    top: int = 50,
) -> list[dict[str, Any]]:
    """Rank tags by frequency and mean likes among notes carrying the tag."""
    counts: Counter[str] = Counter()
    likes_by_tag: dict[str, list[float]] = {}
    for note in notes:
        tags = extract_tags(note)
        note_likes = likes(note)
        for tag in tags:
            counts[tag] += 1
            likes_by_tag.setdefault(tag, []).append(note_likes)

    ranked: list[dict[str, Any]] = []
    for tag, count in counts.most_common(top):
        ranked.append(
            {
                "tag": tag,
                "mentions": count,
                "avg_likes": mean_of(likes_by_tag.get(tag, [])),
            }
        )
    return ranked


def format_rate(value: float | None, *, digits: int = 2) -> str:
    if value is None:
        return "N/A (no view_count)"
    return f"{value * 100:.{digits}f}%"


def format_summary_markdown(summary: dict[str, Any], *, heading: str = "## Summary") -> str:
    lines = [
        heading,
        f"- Notes: {summary['note_count']}",
        f"- Avg / median likes: {summary['avg_likes']:.1f} / {summary['median_likes']:.1f}",
        (
            f"- Avg / median collects: "
            f"{summary['avg_collects']:.1f} / {summary['median_collects']:.1f}"
        ),
        (
            f"- Avg / median comments: "
            f"{summary['avg_comments']:.1f} / {summary['median_comments']:.1f}"
        ),
        f"- Avg engagement rate: {format_rate(summary.get('avg_engagement_rate'))}",
        f"- Avg collect rate: {format_rate(summary.get('avg_collect_rate'))}",
        (
            f"- Viral rate (likes≥{summary['viral_threshold']}): "
            f"{summary['viral_rate'] * 100:.1f}% "
            f"({summary['viral_count']}/{summary['note_count']})"
        ),
    ]
    if summary.get("avg_views") is not None:
        lines.insert(5, f"- Avg views: {summary['avg_views']:.1f}")
    if summary.get("cpv") is not None:
        lines.append(f"- CPV (interactions/cost): {summary['cpv']:.2f}")
    elif summary.get("cost") is not None:
        lines.append("- CPV: N/A")
    return "\n".join(lines) + "\n"
