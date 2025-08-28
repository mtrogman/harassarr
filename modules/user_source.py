from __future__ import annotations
import logging
from typing import Dict, Any, List

from .user_filters import filter_users
from .utils import lower_or_empty


def get_active_users_from_db(db, logger: logging.Logger) -> List[Dict[str, Any]]:
    """
    Adjust the query to your schema. It just needs to return email/discord and dates.
    """
    try:
        q = """
        SELECT primaryEmail AS email,
               primaryDiscord AS discord,
               startDate, endDate,
               planName, fourK
        FROM subscriptions
        WHERE status = 'active'
        """
        rows = db.fetch_all(q)
        return [dict(r) for r in rows]
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to load active users from DB: %s", e)
        return []


def get_shared_users_from_plex(plex_clients: Dict[str, Any], logger: logging.Logger) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for server_name, client in plex_clients.items():
        try:
            for u in client.myPlexAccount().users():
                out.append({
                    "email": getattr(u, "email", None),
                    "username": getattr(u, "username", None) or getattr(u, "title", None),
                    "Server": server_name,     # keep capital S to match your existing dicts
                    "Username": getattr(u, "username", None) or getattr(u, "title", None),
                    "Email": getattr(u, "email", None),
                })
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to enumerate users for %s: %s", server_name, e)
    return out


def build_user_index(db, plex_clients: Dict[str, Any], logger: logging.Logger) -> List[Dict[str, Any]]:
    """
    Merge DB users and Plex users by email (lowercased).
    Skip users missing email (via filter_users).
    """
    db_users   = get_active_users_from_db(db, logger)
    plex_users = get_shared_users_from_plex(plex_clients, logger)

    by_email: Dict[str, Dict[str, Any]] = {}

    for r in db_users:
        email = lower_or_empty(r.get("email") or r.get("primaryEmail"))
        if not email:
            continue
        d = dict(r)
        d["email"] = email
        by_email[email] = d

    for r in plex_users:
        email = lower_or_empty(r.get("email") or r.get("Email"))
        if not email:
            continue
        d = by_email.setdefault(email, {"email": email})
        # keep a username reference if present
        if (r.get("username") or r.get("Username")) and not d.get("username"):
            d["username"] = r.get("username") or r.get("Username")
        # track servers
        servers = set(d.get("servers", []))
        server_name = r.get("server") or r.get("Server")
        if server_name:
            servers.add(server_name)
        d["servers"] = sorted(servers)

    merged = list(by_email.values())
    # Final filter: drop any entries with missing email
    return filter_users(merged, logger=logger)
