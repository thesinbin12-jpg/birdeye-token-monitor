import time
from threading import Lock
from typing import Dict, Any, Optional


_cache: Dict[str, Dict[str, Any]] = {}
_lock = Lock()

DEFAULT_TTL = 300


def get_cached(key: str, ttl: int = DEFAULT_TTL) -> Optional[Dict[str, Any]]:
    with _lock:
        if key in _cache:
            entry = _cache[key]
            if time.time() - entry["timestamp"] < ttl:
                return entry["data"]
            del _cache[key]
    return None


def set_cached(key: str, data: Dict[str, Any]) -> None:
    with _lock:
        _cache[key] = {"data": data, "timestamp": time.time()}


def get_cache_count() -> int:
    with _lock:
        return len(_cache)


def clear_cache() -> int:
    with _lock:
        count = len(_cache)
        _cache.clear()
    return count


def get_cache_stats() -> Dict[str, Any]:
    with _lock:
        now = time.time()
        active = 0
        expired = 0
        for entry in _cache.values():
            if now - entry["timestamp"] < DEFAULT_TTL:
                active += 1
            else:
                expired += 1
        return {
            "total": len(_cache),
            "active": active,
            "expired": expired,
        }
