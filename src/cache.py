"""A tiny in-memory TTL cache.

The app runs as a single instance on Render's free tier, so a process-local
cache is enough — no Redis, no extra cost. Each wrapped function keeps its own
store keyed by its arguments; entries expire after `ttl_seconds`.

`_clock` is injectable so tests can simulate time passing without sleeping.
"""

import time
from functools import wraps


def ttl_cache(ttl_seconds: float, _clock=time.monotonic):
    def decorator(fn):
        store: dict = {}

        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = _clock()
            cached = store.get(key)
            if cached is not None:
                value, ts = cached
                if now - ts < ttl_seconds:
                    return value
            value = fn(*args, **kwargs)
            store[key] = (value, now)
            return value

        wrapper.cache_clear = store.clear
        wrapper.cache_size = lambda: len(store)
        return wrapper

    return decorator
