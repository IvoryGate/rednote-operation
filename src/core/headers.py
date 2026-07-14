"""Rotating browser identity helpers (UA / Accept-Language). No IP proxy pool."""

from __future__ import annotations

import itertools
import random
from collections.abc import Iterator

# Desktop-only UAs. Mobile UAs make Xiaohongshu serve phone UI / QR walls and
# look unlike a normal creator workflow — keep them out of the default pool.
USER_AGENT_POOL: tuple[str, ...] = (
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
)

ACCEPT_LANGUAGE_POOL: tuple[str, ...] = (
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9",
    "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
    "zh-TW,zh;q=0.9,en;q=0.8",
)


class HeaderPool:
    """Round-robin (or random) UA + Accept-Language pairs for crawl contexts."""

    def __init__(
        self,
        user_agents: tuple[str, ...] | None = None,
        accept_languages: tuple[str, ...] | None = None,
        *,
        shuffle: bool = True,
    ) -> None:
        uas = list(user_agents or USER_AGENT_POOL)
        langs = list(accept_languages or ACCEPT_LANGUAGE_POOL)
        if shuffle:
            random.shuffle(uas)
            random.shuffle(langs)
        self._ua_cycle: Iterator[str] = itertools.cycle(uas)
        self._lang_cycle: Iterator[str] = itertools.cycle(langs)

    def next_user_agent(self) -> str:
        return next(self._ua_cycle)

    def next_accept_language(self) -> str:
        return next(self._lang_cycle)

    def next_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.next_user_agent(),
            "Accept-Language": self.next_accept_language(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }


# Process-wide pool shared by crawl scripts.
default_header_pool = HeaderPool()
