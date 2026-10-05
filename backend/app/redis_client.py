"""Thin, failure-tolerant Redis wrapper.

If Redis is unreachable the app keeps working: cache misses fall through to
MySQL and usage counters are written straight to the database.
"""
import json
import time
from typing import Any, Optional

import redis

from .config import settings

_client: Optional[redis.Redis] = None
_down_until = 0.0


def get_redis() -> Optional[redis.Redis]:
    global _client, _down_until
    if time.time() < _down_until:
        return None
    try:
        if _client is None:
            c = redis.Redis.from_url(
                settings.REDIS_URL, decode_responses=True, socket_connect_timeout=0.5, socket_timeout=1
            )
            c.ping()
            _client = c
        return _client
    except Exception:
        _mark_down()
        return None


def _mark_down() -> None:
    global _client, _down_until
    _client = None
    _down_until = time.time() + 15


def cache_get(key: str) -> Optional[Any]:
    r = get_redis()
    if not r:
        return None
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        _mark_down()
        return None


def cache_set(key: str, value: Any, ttl: int) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.set(key, json.dumps(value), ex=ttl)
    except Exception:
        _mark_down()


def cache_delete(*keys: str) -> None:
    r = get_redis()
    if not r or not keys:
        return
    try:
        r.delete(*keys)
    except Exception:
        _mark_down()
