"""Request pacing and exponential backoff for crawl anti-bot resilience."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Enforce a minimum gap between requests; grow the gap when rejected.

    No proxy/IP pool — only pacing + backoff. Call ``wait()`` before each
    navigation, ``on_success()`` after a healthy response, and ``on_reject()``
    when captcha / 403 / rate-limit signals appear.
    """

    min_interval: float = 2.0
    max_interval: float = 60.0
    backoff_factor: float = 2.0
    jitter: float = 0.5
    _interval: float = field(init=False)
    _last_request_at: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        self._interval = self.min_interval

    @property
    def current_interval(self) -> float:
        return self._interval

    def wait(self) -> float:
        """Sleep until the next request is allowed. Returns slept seconds."""
        now = time.monotonic()
        elapsed = now - self._last_request_at
        delay = max(0.0, self._interval - elapsed)
        if self.jitter > 0:
            delay += random.uniform(0, self.jitter)
        if delay > 0:
            time.sleep(delay)
        self._last_request_at = time.monotonic()
        return delay

    def on_success(self) -> None:
        """Decay interval toward the minimum after a healthy response."""
        self._interval = max(self.min_interval, self._interval / self.backoff_factor)

    def on_reject(self) -> None:
        """Double the interval (capped) after a bot-challenge / rate-limit hit."""
        self._interval = min(self.max_interval, self._interval * self.backoff_factor)
