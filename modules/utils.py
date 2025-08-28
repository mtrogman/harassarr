from __future__ import annotations
import logging
import random
import time
from typing import Callable, Iterable, Optional


def lower_or_empty(x: Optional[str]) -> str:
    return x.lower() if isinstance(x, str) else ""


def make_logger(name: str = "harassarr") -> logging.Logger:
    log = logging.getLogger(name)
    if not log.handlers:
        log.setLevel(logging.INFO)
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        log.addHandler(h)
    return log


class Retry:
    def __init__(
        self,
        attempts: int = 5,
        base: float = 0.5,
        max_backoff: float = 8.0,
        retriable_statuses: Iterable[int] = (408, 429, 500, 502, 503, 504),
        logger: Optional[logging.Logger] = None,
    ):
        self.attempts = attempts
        self.base = base
        self.max_backoff = max_backoff
        self.retriable_statuses = set(retriable_statuses)
        self.log = logger or make_logger()

    def _sleep(self, i: int):
        time.sleep(min(self.max_backoff, self.base * (2**i)) + random.random() * 0.2)

    def __call__(self, fn: Callable, *, status_of: Optional[Callable[[Exception], Optional[int]]] = None):
        last = None
        for i in range(self.attempts):
            try:
                return fn()
            except Exception as e:  # noqa: BLE001
                last = e
                status = status_of(e) if status_of else None
                if status is None or status not in self.retriable_statuses:
                    raise
                self.log.warning("Retryable HTTP status %s; retry %d/%d", status, i + 1, self.attempts)
                self._sleep(i)
        if last:
            raise last


def gate_side_effect(dryrun: bool, log: logging.Logger, what: str) -> bool:
    """
    Returns True if you should proceed with the side effect.
    Logs a DRY-RUN line and returns False when dryrun=True.
    """
    if dryrun:
        log.info("DRY-RUN: would do -> %s", what)
        return False
    return True
