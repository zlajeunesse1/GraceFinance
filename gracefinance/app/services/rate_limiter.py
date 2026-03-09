"""
Rate Limiter — Simple in-memory rate limiting for FastAPI.
==========================================================
Lightweight, no external dependencies. Tracks requests per IP
with automatic expiry. For GraceFinance's scale this is sufficient.
At 1000+ concurrent users, swap for Redis-backed solution.

Usage:
    from app.services.rate_limiter import rate_limit

    @router.post("/signup")
    def signup(request: Request, ...):
        rate_limit(request, key="signup", max_requests=3, window_seconds=3600)
        ...
"""

import time
import logging
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

# ── Storage ──────────────────────────────────────────────────────────────────
_lock = Lock()
_requests: dict = defaultdict(list)  # key -> [(timestamp, ...)]

# Cleanup every N calls to prevent unbounded memory growth
_call_count = 0
CLEANUP_INTERVAL = 500


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For from Railway's proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For can be comma-separated; first is the real client
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _cleanup_expired(window_seconds: int):
    """Remove expired entries from all keys. Called periodically."""
    now = time.time()
    expired_keys = []
    for key, timestamps in _requests.items():
        _requests[key] = [t for t in timestamps if now - t < window_seconds]
        if not _requests[key]:
            expired_keys.append(key)
    for key in expired_keys:
        del _requests[key]


def rate_limit(
    request: Request,
    key: str = "default",
    max_requests: int = 10,
    window_seconds: int = 60,
):
    """
    Check rate limit for the given request.
    Raises HTTPException 429 if limit exceeded.

    Args:
        request: FastAPI Request object (used to extract client IP)
        key: Namespace for this limiter (e.g., "login", "signup")
        max_requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds
    """
    global _call_count

    ip = _get_client_ip(request)
    rate_key = f"{key}:{ip}"
    now = time.time()

    with _lock:
        # Periodic cleanup
        _call_count += 1
        if _call_count >= CLEANUP_INTERVAL:
            _cleanup_expired(max(window_seconds, 3600))
            _call_count = 0

        # Filter to only requests within the window
        _requests[rate_key] = [
            t for t in _requests[rate_key]
            if now - t < window_seconds
        ]

        if len(_requests[rate_key]) >= max_requests:
            retry_after = int(window_seconds - (now - _requests[rate_key][0])) + 1
            logger.warning(
                f"Rate limit hit: {rate_key} ({len(_requests[rate_key])}/{max_requests} "
                f"in {window_seconds}s)"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        # Record this request
        _requests[rate_key].append(now)