"""Unit tests for crawl helpers: parsing, rate limit, header pool."""

from __future__ import annotations

from src.core.crawl_parse import (
    ensure_note_id,
    extract_counts_from_text,
    extract_metrics_from_html,
    extract_note_id_from_url,
    note_fields_for_db,
    page_looks_rejected,
    parse_note_card,
    synthesize_note_id,
)
from src.core.headers import USER_AGENT_POOL, HeaderPool
from src.core.rate_limit import RateLimiter


def test_extract_note_id_from_explore_url() -> None:
    url = "https://www.xiaohongshu.com/explore/64f0ab12cd3456789abcdeff"
    assert extract_note_id_from_url(url) == "64f0ab12cd3456789abcdeff"


def test_extract_note_id_from_discovery_url() -> None:
    url = "https://www.xiaohongshu.com/discovery/item/abcdef0123456789abcdef01?xsec=1"
    assert extract_note_id_from_url(url) == "abcdef0123456789abcdef01"


def test_ensure_note_id_from_url() -> None:
    item = {"title": "hello", "url": "https://www.xiaohongshu.com/explore/abcDEF0123456789abcdef01"}
    ensured = ensure_note_id(item)
    assert ensured["note_id"] == "abcDEF0123456789abcdef01"


def test_ensure_note_id_fallback_is_stable() -> None:
    a = ensure_note_id({"title": "同一标题", "url": None})
    b = ensure_note_id({"title": "同一标题", "url": None})
    assert a["note_id"].startswith("synth-")
    assert a["note_id"] == b["note_id"]
    assert a["note_id"] != synthesize_note_id(title="另一个")


def test_note_fields_for_db_filters_unknown_keys() -> None:
    fields = note_fields_for_db(
        {
            "title": "t",
            "url": "https://www.xiaohongshu.com/explore/abcdef0123456789abcdef01",
            "author": "should-drop",
            "cover": "should-drop",
            "like_count": 10,
            "view_count": 999,
        }
    )
    assert fields["note_id"] == "abcdef0123456789abcdef01"
    assert fields["title"] == "t"
    assert fields["like_count"] == 10
    assert fields["view_count"] == 999
    assert "author" not in fields
    assert "cover" not in fields


def test_extract_counts_from_labeled_text() -> None:
    blob = "点赞 1.2万 收藏：300 评论 12 浏览 8.5万"
    counts = extract_counts_from_text(blob)
    assert counts["like_count"] == 12000
    assert counts["collect_count"] == 300
    assert counts["comment_count"] == 12
    assert counts["view_count"] == 85000


def test_extract_metrics_from_html_initial_state() -> None:
    html = """
    <script>window.__INITIAL_STATE__={"note":{"likedCount":88,"collectedCount":9,
    "commentCount":3,"viewCount":1500}}</script>
    """
    metrics = extract_metrics_from_html(html)
    assert metrics["like_count"] == 88
    assert metrics["collect_count"] == 9
    assert metrics["comment_count"] == 3
    assert metrics["view_count"] == 1500


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


class _FakeCard:
    def __init__(self) -> None:
        self._nodes = {
            ".note-title, .title, [class*=title]": _FakeNode(text="测试笔记"),
            ".author, [class*=author], [class*=name]": _FakeNode(text="作者"),
            "img": _FakeNode(src="https://img/x.jpg"),
            "a[href*='/explore/'], a[href*='/discovery/item/'], a": _FakeNode(
                href="/explore/abcdef0123456789abcdef01"
            ),
        }

    def query_selector(self, sel: str) -> _FakeNode | None:
        return self._nodes.get(sel)

    def inner_text(self) -> str:
        return "测试笔记\n点赞 128\n收藏 20\n浏览 5600\n评论 4"


def test_parse_note_card_includes_view_count() -> None:
    item = parse_note_card(_FakeCard())
    assert item["note_id"] == "abcdef0123456789abcdef01"
    assert item["like_count"] == 128
    assert item["view_count"] == 5600
    assert item["collect_count"] == 20
    assert item["comment_count"] == 4
    assert item["view_count_found"] is True
    assert item["like_count_found"] is True


def test_rate_limiter_backoff_and_decay(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    sleeps: list[float] = []
    monkeypatch.setattr("src.core.rate_limit.time.sleep", lambda s: sleeps.append(s))
    # Freeze monotonic progression between waits
    ticks = iter([0.0, 0.0, 10.0, 10.0, 100.0, 100.0])
    monkeypatch.setattr("src.core.rate_limit.time.monotonic", lambda: next(ticks))

    limiter = RateLimiter(min_interval=2.0, max_interval=30.0, backoff_factor=2.0, jitter=0.0)
    assert limiter.current_interval == 2.0

    limiter.on_reject()
    assert limiter.current_interval == 4.0
    limiter.on_reject()
    assert limiter.current_interval == 8.0

    limiter.wait()  # first wait uses raised interval
    assert sleeps[-1] == 8.0

    limiter.on_success()
    assert limiter.current_interval == 4.0
    limiter.on_success()
    assert limiter.current_interval == 2.0


def test_rate_limiter_caps_at_max() -> None:
    limiter = RateLimiter(min_interval=1.0, max_interval=5.0, backoff_factor=10.0, jitter=0.0)
    limiter.on_reject()
    assert limiter.current_interval == 5.0


def test_header_pool_rotates_user_agents() -> None:
    pool = HeaderPool(shuffle=False)
    first = pool.next_user_agent()
    seen = {first}
    for _ in range(len(USER_AGENT_POOL) - 1):
        seen.add(pool.next_user_agent())
    assert len(seen) == len(USER_AGENT_POOL)
    assert pool.next_user_agent() == first  # cycles


def test_header_pool_next_headers_has_required_keys() -> None:
    headers = HeaderPool(shuffle=False).next_headers()
    assert "User-Agent" in headers
    assert "Accept-Language" in headers
    assert "Accept" in headers


class _FakePage:
    def __init__(self, url: str, html: str) -> None:
        self.url = url
        self._html = html

    def content(self) -> str:
        return self._html


def test_page_looks_rejected_detects_captcha() -> None:
    page = _FakePage("https://www.xiaohongshu.com/explore/x", "<html>请完成验证码</html>")
    assert page_looks_rejected(page) is True


def test_page_looks_rejected_login_wall() -> None:
    page = _FakePage(
        "https://www.xiaohongshu.com/search_result?keyword=x",
        "<html>登录后查看搜索结果</html>",
    )
    assert page_looks_rejected(page) is True


def test_page_looks_rejected_ignores_generic_pin_fan() -> None:
    # Lone "频繁" used to false-positive on unrelated copy / JS strings.
    page = _FakePage(
        "https://www.xiaohongshu.com/explore/x",
        "<html>笔记很精彩，内容并不频繁出现</html>",
    )
    assert page_looks_rejected(page) is False


def test_page_looks_rejected_clean_page() -> None:
    page = _FakePage("https://www.xiaohongshu.com/explore/x", "<html>正常笔记内容</html>")
    assert page_looks_rejected(page) is False
