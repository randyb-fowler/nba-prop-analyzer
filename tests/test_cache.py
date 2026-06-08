"""Unit tests for the TTL cache. Uses a fake clock so no real time passes."""

from src.cache import ttl_cache


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def test_caches_repeated_calls():
    clock = FakeClock()
    calls = {"n": 0}

    @ttl_cache(100, _clock=clock)
    def f(x):
        calls["n"] += 1
        return x * 2

    assert f(5) == 10
    assert f(5) == 10
    assert calls["n"] == 1  # second call served from cache


def test_distinct_args_cached_separately():
    clock = FakeClock()
    calls = {"n": 0}

    @ttl_cache(100, _clock=clock)
    def f(x):
        calls["n"] += 1
        return x

    f(1); f(2); f(1)
    assert calls["n"] == 2


def test_entry_expires_after_ttl():
    clock = FakeClock()
    calls = {"n": 0}

    @ttl_cache(100, _clock=clock)
    def f(x):
        calls["n"] += 1
        return x

    f(1)
    clock.advance(99)
    f(1)              # still fresh
    assert calls["n"] == 1
    clock.advance(2)  # now past ttl (101 > 100)
    f(1)
    assert calls["n"] == 2


def test_kwargs_keyed_consistently():
    clock = FakeClock()
    calls = {"n": 0}

    @ttl_cache(100, _clock=clock)
    def f(a, b=1):
        calls["n"] += 1
        return a + b

    f(1, b=2)
    f(1, b=2)
    assert calls["n"] == 1


def test_cache_clear_and_size():
    clock = FakeClock()

    @ttl_cache(100, _clock=clock)
    def f(x):
        return x

    f(1); f(2)
    assert f.cache_size() == 2
    f.cache_clear()
    assert f.cache_size() == 0
