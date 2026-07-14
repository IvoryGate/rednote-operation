"""Shared Xiaohongshu note / card parsing helpers for crawl scripts."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse

NOTE_ID_PATTERNS = (
    re.compile(r"/explore/([a-fA-F0-9]{16,})"),
    re.compile(r"/discovery/item/([a-fA-F0-9]{16,})"),
    re.compile(r"/search_result/([a-fA-F0-9]{16,})"),
    re.compile(r"[?&]note[_-]?id=([a-fA-F0-9]{16,})", re.IGNORECASE),
)

REJECT_MARKERS = (
    "访问频次异常",
    "访问过于频繁",
    "操作过于频繁",
    "验证码",
    "captcha",
    "403 Forbidden",
    "请登录后查看",
    "登录后查看搜索结果",
    "登录后查看",
    "当前笔记暂时无法浏览",
)


def extract_note_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    for pattern in NOTE_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def synthesize_note_id(*, url: str | None = None, title: str | None = None) -> str:
    """Stable fallback id when the page does not expose a platform note id."""
    seed = (url or "").strip() or (title or "").strip() or "unknown"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:24]
    return f"synth-{digest}"


def ensure_note_id(item: dict[str, Any]) -> dict[str, Any]:
    """Guarantee ``note_id`` is present for DB inserts."""
    note_id = item.get("note_id") or extract_note_id_from_url(item.get("url"))
    if not note_id:
        note_id = synthesize_note_id(url=item.get("url"), title=item.get("title"))
    item["note_id"] = note_id
    return item


def _card_href(card: Any) -> str | None:
    link = card.query_selector("a[href*='/explore/'], a[href*='/discovery/item/'], a")
    if not link:
        return None
    href = link.get_attribute("href") or ""
    if href.startswith("//"):
        return f"https:{href}"
    if href.startswith("/"):
        return f"https://www.xiaohongshu.com{href}"
    if href.startswith("http"):
        return href
    return None


def _parse_count(text: str | None) -> int:
    if not text:
        return 0
    text = text.strip().replace(",", "")
    match = re.search(r"([\d.]+)\s*万", text)
    if match:
        return int(float(match.group(1)) * 10000)
    # "1.2亿" style (rare for note views but harmless)
    match = re.search(r"([\d.]+)\s*亿", text)
    if match:
        return int(float(match.group(1)) * 100_000_000)
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def _count_or_none(text: str | None) -> int | None:
    """Parse a count from text; return None when no digits are present."""
    if not text or not str(text).strip():
        return None
    parsed = _parse_count(text)
    # Empty / non-numeric texts already returned 0 from _parse_count with no digits.
    if parsed == 0 and not re.search(r"\d", str(text)):
        return None
    return parsed


def metric_hit_stats(
    notes: list[dict[str, Any]],
    *,
    field: str = "view_count",
) -> dict[str, Any]:
    """Summarize extraction hit-rate for a metric field across parsed notes.

    Prefer ``{field}_found`` boolean flags when present (set by card parsing).
    Otherwise a hit is a present numeric value that is not the empty/missing
    sentinel. For plain JSON exports without flags, ``view_count > 0`` is also
    reported as ``positive_rate`` for a practical live-signal check.
    """
    total = len(notes)
    hits = 0
    positive = 0
    misses = 0
    flag_key = f"{field}_found"
    for note in notes:
        if flag_key in note:
            found = bool(note.get(flag_key))
            if found:
                hits += 1
                try:
                    if int(note.get(field) or 0) > 0:
                        positive += 1
                except (TypeError, ValueError):
                    pass
            else:
                misses += 1
            continue

        raw = note.get(field, None)
        if raw is None or raw == "":
            misses += 1
            continue
        try:
            value = int(raw)
        except (TypeError, ValueError):
            misses += 1
            continue
        hits += 1
        if value > 0:
            positive += 1
    rate = (hits / total) if total else 0.0
    positive_rate = (positive / total) if total else 0.0
    return {
        "field": field,
        "total": total,
        "hits": hits,
        "misses": misses,
        "positive": positive,
        "hit_rate": round(rate, 4),
        "positive_rate": round(positive_rate, 4),
    }


def _first_text(card: Any, selectors: str) -> str | None:
    el = card.query_selector(selectors)
    if not el:
        return None
    try:
        return el.inner_text()
    except Exception:
        return el.get_attribute("content") if hasattr(el, "get_attribute") else None


def _metric_from_labeled_text(blob: str, labels: tuple[str, ...]) -> int | None:
    """Parse counts next to Chinese labels inside a text blob."""
    for label in labels:
        # e.g. "浏览 1.2万" / "点赞12" / "收藏：3"
        pattern = rf"{label}\s*[:：]?\s*([\d.]+)\s*([万亿]?)"
        match = re.search(pattern, blob)
        if match:
            num = float(match.group(1))
            unit = match.group(2)
            if unit == "万":
                return int(num * 10000)
            if unit == "亿":
                return int(num * 100_000_000)
            return int(num)
    return None


def extract_counts_from_text(blob: str | None) -> dict[str, int]:
    """Best-effort metric extraction from free text / card aria labels."""
    if not blob:
        return {}
    counts: dict[str, int] = {}
    mapping = {
        "view_count": ("浏览", "阅读", "观看", "曝光", "view"),
        "like_count": ("点赞", "喜欢", "赞", "like"),
        "collect_count": ("收藏", "collect"),
        "comment_count": ("评论", "comment"),
        "share_count": ("分享", "转发", "share"),
    }
    for key, labels in mapping.items():
        value = _metric_from_labeled_text(blob, labels)
        if value is not None:
            counts[key] = value
    return counts


def extract_metrics_from_html(html: str | None) -> dict[str, int]:
    """Pull note metrics from embedded JSON blobs when present."""
    if not html:
        return {}
    counts: dict[str, int] = {}

    # Common note detail keys in XHS SPA state.
    patterns = {
        "view_count": (
            r'"(?:viewCount|view_count|readCount|read_count)"\s*:\s*(\d+)',
            r'"impressionCount"\s*:\s*(\d+)',
        ),
        "like_count": (r'"(?:likedCount|likeCount|like_count)"\s*:\s*(\d+)',),
        "collect_count": (r'"(?:collectedCount|collectCount|collect_count)"\s*:\s*(\d+)',),
        "comment_count": (r'"(?:commentCount|commentsCount|comment_count)"\s*:\s*(\d+)',),
        "share_count": (r'"(?:shareCount|sharedCount|share_count)"\s*:\s*(\d+)',),
    }
    for key, pats in patterns.items():
        for pat in pats:
            match = re.search(pat, html)
            if match:
                counts[key] = int(match.group(1))
                break

    # Fallback: labeled Chinese text in HTML
    text_counts = extract_counts_from_text(re.sub(r"<[^>]+>", " ", html))
    for key, value in text_counts.items():
        counts.setdefault(key, value)
    return counts


def parse_note_card(card: Any) -> dict[str, Any]:
    title_el = card.query_selector(".note-title, .title, [class*=title]")
    author_el = card.query_selector(".author, [class*=author], [class*=name]")
    like_el = card.query_selector(
        "[class*=like] [class*=count], [class*=like-count], [class*=like] span, [class*=like]"
    )
    view_el = card.query_selector(
        "[class*=view] [class*=count], [class*=view-count], [class*=read], [class*=impression]"
    )
    collect_el = card.query_selector(
        "[class*=collect] [class*=count], [class*=collect-count], [class*=collect]"
    )
    comment_el = card.query_selector(
        "[class*=comment] [class*=count], [class*=comment-count], [class*=comment]"
    )
    img_el = card.query_selector("img")
    href = _card_href(card)
    title = title_el.inner_text().strip() if title_el else ""

    card_text = ""
    try:
        card_text = card.inner_text()
    except Exception:
        card_text = ""
    labeled = extract_counts_from_text(card_text)

    like_count = labeled.get("like_count")
    if like_count is None:
        like_count = _count_or_none(like_el.inner_text() if like_el else None)

    view_count = labeled.get("view_count")
    if view_count is None:
        view_raw = view_el.inner_text() if view_el else None
        if not view_raw:
            view_raw = _first_text(card, "[aria-label*=浏览], [aria-label*=阅读]")
        view_count = _count_or_none(view_raw)

    collect_count = labeled.get("collect_count")
    if collect_count is None:
        collect_count = _count_or_none(collect_el.inner_text() if collect_el else None)

    comment_count = labeled.get("comment_count")
    if comment_count is None:
        comment_count = _count_or_none(comment_el.inner_text() if comment_el else None)

    item: dict[str, Any] = {
        "title": title,
        "author": author_el.inner_text().strip() if author_el else "",
        "cover": img_el.get_attribute("src") if img_el else "",
        "like_count": like_count if like_count is not None else 0,
        "view_count": view_count if view_count is not None else 0,
        "collect_count": collect_count if collect_count is not None else 0,
        "comment_count": comment_count if comment_count is not None else 0,
        # Presence flags for hit-rate probes (True when extracted, not defaulted).
        "view_count_found": view_count is not None,
        "like_count_found": like_count is not None,
        "url": href,
        "note_id": extract_note_id_from_url(href),
    }
    return ensure_note_id(item)


def extract_notes_from_list(page: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    try:
        cards = page.query_selector_all(
            "section.note-item, section.reds-note-card, .note-item, [class*=note-item]"
        )
        for card in cards:
            try:
                results.append(parse_note_card(card))
            except Exception:
                continue
    except Exception:
        return results
    return results


def extract_note_detail(page: Any) -> dict[str, Any]:
    try:
        title_el = page.query_selector("#detail-title, .title, h1")
        if not title_el:
            title_el = page.query_selector("title")
        content_el = page.query_selector("#detail-desc, .desc, meta[name=description]")
        title = ""
        content = ""
        if title_el:
            title = title_el.inner_text() if hasattr(title_el, "inner_text") else ""
            if not title and title_el.get_attribute:
                title = title_el.get_attribute("content") or title_el.inner_text()
        if content_el:
            content = content_el.get_attribute("content") or content_el.inner_text()

        html = ""
        try:
            html = page.content()
        except Exception:
            html = ""
        metrics = extract_metrics_from_html(html)

        data: dict[str, Any] = {
            "title": (title or "").strip(),
            "content": (content or "").strip(),
            "url": page.url,
            "note_id": extract_note_id_from_url(page.url),
            "like_count": metrics.get("like_count", 0),
            "collect_count": metrics.get("collect_count", 0),
            "comment_count": metrics.get("comment_count", 0),
            "share_count": metrics.get("share_count", 0),
            "view_count": metrics.get("view_count", 0),
        }
        return ensure_note_id(data)
    except Exception:
        url = getattr(page, "url", None)
        return ensure_note_id({"title": "", "content": "", "url": url})


def page_looks_rejected(page: Any) -> bool:
    """Heuristic: captcha / rate-limit / forced-login interstitial."""
    try:
        url = (page.url or "").lower()
        if "captcha" in url or "login" in urlparse(url).path:
            # login redirect after an authenticated session is suspicious for crawl pages
            if "login" in url and "xiaohongshu.com" in url:
                return True
        body = page.content()
        lowered = body.lower()
        for marker in REJECT_MARKERS:
            if marker.lower() in lowered:
                return True
    except Exception:
        return False
    return False


def note_fields_for_db(item: dict[str, Any]) -> dict[str, Any]:
    """Map a parsed note dict onto ORM Note column names."""
    ensured = ensure_note_id(dict(item))
    allowed = {
        "note_id",
        "account_id",
        "title",
        "content",
        "images",
        "video_url",
        "tags",
        "topics",
        "like_count",
        "collect_count",
        "comment_count",
        "share_count",
        "view_count",
        "is_original",
        "url",
        "published_at",
    }
    return {k: v for k, v in ensured.items() if k in allowed and v is not None}
