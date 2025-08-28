# modules/plex_filters.py
from __future__ import annotations
import logging
from typing import Dict, Iterable, Iterator, Optional

from modules.snapshot import SnapshotLog
from modules.normalize import normalize_email, safe_strip

logger = logging.getLogger(__name__)

def actionable_from_plex(
    plex_user_dicts: Iterable[Dict],
    server_display_name: str,
    snapshot: SnapshotLog,
) -> Iterator[Dict]:
    server_display_name = safe_strip(server_display_name)
    for user in plex_user_dicts:
        email = normalize_email(user.get("Email"))
        username = user.get("Username")
        plex_user_id = user.get("User ID")

        if not email:
            # Skip non-actionable local/managed accounts with no email
            snapshot.add(
                user_id=str(plex_user_id) if plex_user_id is not None else None,
                username=username,
                email=None,
                server=server_display_name,
                skipped_reason="no_email",
            )
            logger.debug(
                "Skipping Plex user '%s' on server '%s' (no email; likely local/managed).",
                username, server_display_name
            )
            continue

        # Normalize back onto the dict so downstream always has a clean value
        user["Email"] = email
        user["Server"] = server_display_name or user.get("Server")
        yield user
