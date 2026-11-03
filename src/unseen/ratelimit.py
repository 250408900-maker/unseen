"""A small in-memory sliding-window rate limiter."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable


class RateLimiter:
    """Allow at most `limit` hits per `window` seconds for each key (for example an IP)."""

    def __init__(
        self,
        limit: int,
        window: float,
        *,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window = window
        self.max_keys = max_keys
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> float:
        """Record a hit. Return 0 if allowed, otherwise the seconds to wait before retrying."""
        now = self._clock()
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                if len(self._hits) >= self.max_keys:
                    self._prune(now)
                    if len(self._hits) >= self.max_keys:
                        return self.window  # too many distinct clients: refuse new ones
                hits = self._hits[key] = deque()

            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return self.window - (now - hits[0])  # blocked hits are not recorded

            hits.append(now)
            return 0.0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def _prune(self, now: float) -> None:
        stale = [k for k, hits in self._hits.items() if not hits or now - hits[-1] >= self.window]
        for key in stale:
            del self._hits[key]