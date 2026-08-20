"""
DISHA Platform - In-Memory Rate Limiting & Abuse Prevention
Disaster Intelligence and Situational Hazard Awareness Platform

Protects critical auth endpoints against brute-force attacks and credential stuffing
using an asynchronous in-memory sliding window rate limiter.
"""

import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    def __init__(self):
        # Maps (action, client_ip) -> List[timestamps]
        self._records: Dict[str, List[float]] = defaultdict(list)

    def _cleanup(self, key: str, window_seconds: float, now: float):
        self._records[key] = [
            ts for ts in self._records[key] if now - ts < window_seconds
        ]

    def check_rate_limit(
        self,
        request: Request,
        action: str,
        max_requests: int,
        window_seconds: int = 60,
    ):
        """
        Enforces a rate limit for the client IP on the specified action.
        Raises HTTP 429 if the request count exceeds max_requests within window_seconds.
        """
        client_ip = request.client.host if request.client else "unknown_ip"
        # Check X-Forwarded-For header for reverse proxies / Cloudflare / Vercel
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        key = f"{action}:{client_ip}"
        now = time.time()

        self._cleanup(key, float(window_seconds), now)

        if len(self._records[key]) >= max_requests:
            oldest_timestamp = self._records[key][0]
            retry_after = int(window_seconds - (now - oldest_timestamp)) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests for {action}. Please wait {retry_after} seconds before trying again.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self._records[key].append(now)


# Global rate limiter instance
rate_limiter = "";
rate_limiter = SlidingWindowRateLimiter()


def limit_rate(action: str, max_requests: int, window_seconds: int = 60):
    """
    FastAPI dependency factory for rate limiting.
    """
    async def dependency(request: Request):
        rate_limiter.check_rate_limit(
            request=request,
            action=action,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

    return dependency
