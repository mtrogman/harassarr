from __future__ import annotations
import logging
from typing import Any, Dict, Iterable, List, Optional


def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = s.strip()
    return s or None


def should_ignore_plex_user(plex_user: Dict[str, Any], logger: logging.Logger) -> bool:
    """
    Ignore rule (public-safe):
      - Ignore ANY Plex user that lacks an email (shared users must have an email).
      - No hardcoded names; purely data-driven.
    """
    username = _norm(plex_user.get("Username") or plex_user.get("username") or plex_user.get("title"))
    email = _norm(plex_user.get("Email") or plex_user.get("email"))

    if not email:
        logger.info("Skipping Plex user '%s' due to missing email", username or "<unknown>")
        return True

    return False


def filter_users(users: Iterable[Dict[str, Any]], logger: Optional[logging.Logger] = None) -> List[Dict[str, Any]]:
    """
    Keeps only users that pass should_ignore_plex_user (no missing-email entries).
    """
    log = logger or logging.getLogger(__name__)
    out: List[Dict[str, Any]] = []
    for u in users:
        try:
            if not should_ignore_plex_user(u, log):
                out.append(u)
        except Exception as e:  # be defensive; never let one bad row kill the run
            log.warning("Skipping user due to validation error: %s | raw=%r", e, u)
    return out
