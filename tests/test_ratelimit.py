import pytest

from unseen.ratelimit import RateLimiter


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make(limit=2, window=60.0, **kwargs):
    clock = Clock()
    return RateLimiter(limit, window, clock=clock, **kwargs), clock


def test_allows_up_to_the_limit_then_blocks():
    limiter, _ = make()
    assert limiter.check("a") == 0
    assert limiter.check("a") == 0
    assert limiter.check("a") > 0


def test_retry_time_counts_down_to_the_oldest_hit():
    limiter, clock = make()
    limiter.check("a")  # t=0
    clock.now = 10
    limiter.check("a")
    clock.now = 20
    assert limiter.check("a") == pytest.approx(40)


def test_allowed_again_after_the_window():
    limiter, clock = make()
    limiter.check("a")
    limiter.check("a")
    clock.now = 61
    assert limiter.check("a") == 0


def test_keys_are_independent():
    limiter, _ = make(limit=1)
    assert limiter.check("a") == 0
    assert limiter.check("a") > 0
    assert limiter.check("b") == 0


def test_blocked_attempts_do_not_extend_the_block():
    limiter, clock = make(limit=1)
    limiter.check("a")  # t=0
    clock.now = 30
    assert limiter.check("a") > 0  # refused, and not recorded
    clock.now = 60
    assert limiter.check("a") == 0


def test_new_keys_are_refused_when_the_table_is_full_until_entries_expire():
    limiter, clock = make(limit=1, max_keys=2)
    assert limiter.check("a") == 0
    assert limiter.check("b") == 0
    assert limiter.check("c") > 0
    clock.now = 61
    assert limiter.check("c") == 0


def test_reset_clears_everything():
    limiter, _ = make(limit=1)
    limiter.check("a")
    assert limiter.check("a") > 0
    limiter.reset()
    assert limiter.check("a") == 0