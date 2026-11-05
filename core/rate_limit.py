"""
core/rate_limit.py - Token-bucket rate limiting middleware.

Implemented using a pure-Python in-memory token bucket (no new third-party
dependencies). Each "bucket" is keyed by (client_ip, endpoint_group).

Limits (per-IP, sliding window via token bucket):
  - SOS:          5  requests / 60 s  (safety critical – don't hammer)
  - Auth-write:   10 requests / 60 s  (register, verify endpoints)
  - Default:     120 requests / 60 s  (all other authenticated API calls)

The middleware adds the following response headers on every request:
  X-RateLimit-Limit:     bucket capacity
  X-RateLimit-Remaining: tokens remaining after this request
  X-RateLimit-Reset:     Unix timestamp when the bucket refills

Behaviour in rate-limited state:
  - Returns HTTP 429 with {"detail": "Rate limit exceeded. Try again later."}
  - Adds Retry-After header (seconds until next token available)

Thread safety: protected with threading.Lock per bucket.
"""

import time
import threading
from typing import Dict, Tuple

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# ---------------------------------------------------------------------------
# Bucket configuration  (capacity, refill_rate tokens/second)
# ---------------------------------------------------------------------------
_BUCKET_CONFIGS: Dict[str, Tuple[float, float]] = {
    "sos":        (5,   5 / 60),    # 5 req / 60 s
    "auth_write": (10, 10 / 60),    # 10 req / 60 s
    "default":    (120, 120 / 60),  # 120 req / 60 s
}


def _endpoint_group(path: str, method: str) -> str:
    """Map a request path+method to a named rate-limit group."""
    if path.endswith("/sos") or "/sos" in path:
        return "sos"
    if method == "POST" and (
        path.endswith("/register")
        or path.endswith("/verify")
        or "/verifications/" in path
    ):
        return "auth_write"
    return "default"


class _TokenBucket:
    """Thread-safe token bucket for a single (ip, group) pair."""

    __slots__ = ("_capacity", "_rate", "_tokens", "_last_refill", "_lock")

    def __init__(self, capacity: float, rate: float) -> None:
        self._capacity = capacity
        self._rate = rate          # tokens per second
        self._tokens = capacity    # start full
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def consume(self) -> Tuple[bool, float, float]:
        """
        Try to consume one token.

        Returns:
            (allowed, remaining, retry_after_seconds)
        """
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._last_refill = now

            if self._tokens >= 1:
                self._tokens -= 1
                return True, self._tokens, 0.0
            else:
                retry_after = (1 - self._tokens) / self._rate
                return False, 0.0, retry_after


# Global registry of buckets  { (ip, group) -> _TokenBucket }
_buckets: Dict[Tuple[str, str], _TokenBucket] = {}
_registry_lock = threading.Lock()


def _get_bucket(ip: str, group: str) -> _TokenBucket:
    key = (ip, group)
    with _registry_lock:
        if key not in _buckets:
            capacity, rate = _BUCKET_CONFIGS[group]
            _buckets[key] = _TokenBucket(capacity, rate)
        return _buckets[key]


def _client_ip(request: Request) -> str:
    """Extract the best-effort real client IP."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that enforces per-IP token-bucket rate limiting.

    Skips rate limiting for:
    - /health, /docs, /openapi.json, /redoc  (operational endpoints)
    - /api/health, /api/docs variants
    """

    _SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc",
                   "/api/health", "/api/docs", "/api/openapi.json", "/api/redoc", "/"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Skip rate limiting for operational/static paths
        if path in self._SKIP_PATHS or path.startswith("/static"):
            return await call_next(request)

        ip = _client_ip(request)
        group = _endpoint_group(path, method)
        bucket = _get_bucket(ip, group)
        capacity, _ = _BUCKET_CONFIGS[group]

        allowed, remaining, retry_after = bucket.consume()

        if not allowed:
            reset_ts = int(time.time() + retry_after)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": str(int(capacity)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_ts),
                },
            )

        response: Response = await call_next(request)
        reset_ts = int(time.time() + (capacity - remaining) / (capacity / 60))
        response.headers["X-RateLimit-Limit"] = str(int(capacity))
        response.headers["X-RateLimit-Remaining"] = str(int(remaining))
        response.headers["X-RateLimit-Reset"] = str(reset_ts)
        return response


def clear_all_buckets() -> None:
    """Test helper: wipe all in-memory buckets so tests start fresh."""
    with _registry_lock:
        _buckets.clear()

