# modules/util_retry.py
from __future__ import annotations
import asyncio
from typing import Callable, Awaitable, Set

TRANSIENT_STATUSES: Set[int] = {408, 429, 500, 502, 503, 504}

async def with_retries(coro_factory: Callable[[], Awaitable], *, retries: int = 3, base_delay: float = 0.5):
    """
    Minimal async retry wrapper for transient HTTP-ish failures.
    Expects exceptions with optional 'status' attribute.
    """
    attempt = 0
    while True:
        try:
            return await coro_factory()
        except Exception as e:
            status = getattr(e, "status", None)
            if status in TRANSIENT_STATUSES and attempt < retries:
                await asyncio.sleep(base_delay * (2 ** attempt))
                attempt += 1
                continue
            raise
