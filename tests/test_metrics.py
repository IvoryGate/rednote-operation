"""Unit tests for analysis metrics helpers."""

from __future__ import annotations

from src.core.metrics import (
    collect_rate,
    cpv,
    engagement_rate,
    enrich_note,
    extract_tags,
    format_rate,
    format_summary_markdown,
    summarize_notes,
    tag_insights,
    viral_rate,
)

SAMPLE = [
    {
        "title": "A #美食",
        "tags": "探店,美食",
        "like_count": 2000,
        "collect_count": 400,
        "comment_count": 100,
        "view_count": 10000,
    },
    {
        "title": "B",
        "tags": ["探店"],
        "like_count": 100,
        "collect_count": 20,
        "comment_count": 5,
        "view_count": 2000,
    },
    {
        "title": "C #旅行 #美食",
        "like_count": 50,
        "collect_count": 10,
        "comment_count": 2,
        # no views
    },
]


def test_engagement_and_collect_rate() -> None:
    note = SAMPLE[0]
    assert engagement_rate(note) == (2000 + 400 + 100) / 10000
    assert collect_rate(note) == 400 / 10000
    assert engagement_rate(SAMPLE[2]) is None
    assert collect_rate(SAMPLE[2]) is None


def test_viral_rate() -> None:
    assert viral_rate(SAMPLE, threshold=1000) == 1 / 3
    assert viral_rate([], threshold=1000) == 0.0


def test_cpv() -> None:
    assert cpv(SAMPLE, cost=10) == (2500 + 125 + 62) / 10
    assert cpv(SAMPLE, cost=0) is None


def test_summarize_notes() -> None:
    summary = summarize_notes(SAMPLE, viral_threshold=1000, cost=10)
    assert summary["note_count"] == 3
    assert summary["median_likes"] == 100
    assert summary["viral_count"] == 1
    assert summary["notes_with_views"] == 2
    assert summary["avg_engagement_rate"] is not None
    assert summary["cpv"] is not None


def test_enrich_note() -> None:
    out = enrich_note(SAMPLE[0])
    assert out["interactions"] == 2500
    assert out["engagement_rate"] is not None


def test_extract_tags_from_fields_and_hashtags() -> None:
    tags = extract_tags(SAMPLE[0])
    assert "探店" in tags
    assert "美食" in tags
    tags_c = extract_tags(SAMPLE[2])
    assert "旅行" in tags_c
    assert "美食" in tags_c


def test_tag_insights_ranks_and_avg_likes() -> None:
    ranked = tag_insights(SAMPLE, top=10)
    by_tag = {r["tag"]: r for r in ranked}
    assert by_tag["探店"]["mentions"] == 2
    assert by_tag["探店"]["avg_likes"] == (2000 + 100) / 2
    assert by_tag["美食"]["mentions"] == 2


def test_format_helpers() -> None:
    assert format_rate(None) == "N/A (no view_count)"
    assert format_rate(0.1234) == "12.34%"
    md = format_summary_markdown(summarize_notes(SAMPLE))
    assert "Viral rate" in md
    assert "Avg engagement rate" in md
