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
    "频繁",
    "验证码",
    "captcha",
    "403 Forbidden",
    "请登录后查看",
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
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def parse_note_card(card: Any) -> dict[str, Any]:
    title_el = card.query_selector(".note-title, .title, [class*=title]")
    author_el = card.query_selector(".author, [class*=author], [class*=name]")
    like_el = card.query_selector("[class*=like], .like-wrapper, [class*=count]")
    img_el = card.query_selector("img")
    href = _card_href(card)
    title = title_el.inner_text().strip() if title_el else ""
    item: dict[str, Any] = {
        "title": title,
        "author": author_el.inner_text().strip() if author_el else "",
        "cover": img_el.get_attribute("src") if img_el else "",
        "like_count": _parse_count(like_el.inner_text() if like_el else None),
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
        data: dict[str, Any] = {
            "title": (title or "").strip(),
            "content": (content or "").strip(),
            "url": page.url,
            "note_id": extract_note_id_from_url(page.url),
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
