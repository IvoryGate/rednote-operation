"""Tests for view_count hit-rate probe helpers and CLI offline mode."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from scripts.crawl.probe_view_count import main
from src.core.crawl_parse import metric_hit_stats, parse_note_card


def test_metric_hit_stats_with_found_flags() -> None:
    notes: list[dict[str, Any]] = [
        {"view_count": 100, "view_count_found": True},
        {"view_count": 0, "view_count_found": False},
        {"view_count": 0, "view_count_found": True},
    ]
    stats = metric_hit_stats(notes, field="view_count")
    assert stats["total"] == 3
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["positive"] == 1
    assert stats["hit_rate"] == 0.6667


def test_metric_hit_stats_without_flags_uses_presence() -> None:
    notes: list[dict[str, Any]] = [
        {"view_count": 10},
        {"view_count": None},
        {"view_count": 0},
        {},
    ]
    stats = metric_hit_stats(notes, field="view_count")
    assert stats["hits"] == 2  # 10 and 0
    assert stats["misses"] == 2
    assert stats["positive"] == 1


class _FakeNode:
    def __init__(self, *, text: str = "", href: str | None = None, src: str | None = None) -> None:
        self._text = text
        self._href = href
        self._src = src

    def inner_text(self) -> str:
        return self._text

    def get_attribute(self, name: str) -> str | None:
        if name == "href":
            return self._href
        if name == "src":
            return self._src
        return None


_LIKE_SEL = "[class*=like] [class*=count], [class*=like-count], [class*=like] span, [class*=like]"


class _CardNoViews:
    def query_selector(self, sel: str) -> _FakeNode | None:
        nodes = {
            ".note-title, .title, [class*=title]": _FakeNode(text="无浏览"),
            ".author, [class*=author], [class*=name]": _FakeNode(text="作者"),
            "img": _FakeNode(src="https://img/x.jpg"),
            "a[href*='/explore/'], a[href*='/discovery/item/'], a": _FakeNode(
                href="/explore/abcdef0123456789abcdef01"
            ),
            _LIKE_SEL: _FakeNode(text="12"),
        }
        return nodes.get(sel)

    def inner_text(self) -> str:
        return "无浏览\n点赞 12"


def test_parse_note_card_sets_view_found_false_when_absent() -> None:
    item = parse_note_card(_CardNoViews())
    assert item["like_count"] == 12
    assert item["like_count_found"] is True
    assert item["view_count"] == 0
    assert item["view_count_found"] is False


def test_probe_cli_offline(tmp_path: Path) -> None:
    path = tmp_path / "notes.json"
    path.write_text(
        json.dumps(
            [
                {
                    "title": "a",
                    "view_count": 100,
                    "view_count_found": True,
                    "like_count": 1,
                    "like_count_found": True,
                },
                {
                    "title": "b",
                    "view_count": 0,
                    "view_count_found": False,
                    "like_count": 2,
                    "like_count_found": True,
                },
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(
        main, ["--input", str(path), "--json-out", str(out), "--min-hit-rate", "0.4"]
    )
    assert result.exit_code == 0, result.output
    assert "PROBE OK" in result.output
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["metrics"]["view_count"]["hit_rate"] == 0.5
