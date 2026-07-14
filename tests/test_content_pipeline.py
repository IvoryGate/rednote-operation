"""Tests for brief → finalize content pipeline helpers."""

from __future__ import annotations

from src.core.content_pipeline import (
    BODY_MIN_CHARS,
    append_hashtags,
    build_publish_draft,
    extract_post_fields,
    validate_post,
)


def _long_body(paragraphs: int = 3) -> str:
    chunk = "这是一段用于测试的正文内容，补充字数以满足质量门槛。" * 4
    return ("\n\n").join([chunk for _ in range(paragraphs)])


def test_extract_from_brief_generated() -> None:
    data = {
        "meta": {"topic": "t"},
        "generated": {
            "title": "周末探店",
            "body": _long_body(),
            "tags": ["美食", "探店", "周末", "推荐", "打卡"],
        },
    }
    fields = extract_post_fields(data)
    assert fields["title"] == "周末探店"
    assert len(fields["tags"]) == 5


def test_extract_from_finalized_draft() -> None:
    data = {"title": "标题", "content": "正文", "tags": ["a", "b"], "images": ["1.png"]}
    fields = extract_post_fields(data)
    assert fields["body"] == "正文"
    assert fields["images"] == ["1.png"]


def test_append_hashtags_adds_missing_only() -> None:
    body = "正文内容 #美食"
    out = append_hashtags(body, ["美食", "探店"])
    assert "#探店" in out
    assert out.count("#美食") == 1


def test_validate_post_quality_gates() -> None:
    good = {
        "title": "短标题可以",
        "body": _long_body(),
        "tags": ["a", "b", "c", "d", "e"],
        "images": [],
    }
    assert validate_post(good) == []

    bad = {"title": "x" * 30, "body": "短", "tags": ["a"], "images": []}
    issues = validate_post(bad)
    assert any("title length" in i for i in issues)
    assert any(f"< {BODY_MIN_CHARS}" in i for i in issues)
    assert any("tags count" in i for i in issues)


def test_build_publish_draft_shape() -> None:
    brief = {
        "generated": {
            "title": "周末探店",
            "body": _long_body(),
            "tags": ["美食", "探店", "周末", "推荐", "打卡"],
        }
    }
    draft = build_publish_draft(brief, images=["a.png", "b.png"])
    assert draft["title"] == "周末探店"
    assert draft["status"] == "final"
    assert "#美食" in draft["content"]
    assert draft["images"] == ["a.png", "b.png"]
