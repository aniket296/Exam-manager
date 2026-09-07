import time
from collections import defaultdict
from fastapi import Request, HTTPException, status
from typing import Dict, List, Tuple
import threading

class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Keyed by client IP and endpoint path.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        now = time.time()
        window_start = now - window_seconds
        with self._lock:
            # Clean up old timestamps
            self._requests[key] = [t for t in self._requests[key] if t > window_start]
            current_count = len(self._requests[key])
            if current_count >= max_requests:
                retry_after = int(window_seconds - (now - self._requests[key][0])) + 1
                return False, max(1, retry_after)
            self._requests[key].append(now)
            return True, 0

rate_limiter = SlidingWindowRateLimiter()

def check_rate_limit(request: Request, max_requests: int = 10, window_seconds: int = 60):
    """
    FastAPI dependency to rate limit requests.
    Raises HTTP 429 Too Many Requests if threshold is exceeded.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    key = f"{client_ip}:{path}"
    allowed, retry_after = rate_limiter.is_allowed(key, max_requests, window_seconds)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )

