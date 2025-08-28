# modules/normalize.py
from __future__ import annotations
from typing import Optional

def normalize_server_key(name: Optional[str]) -> str:
    """Case/whitespace-insensitive canonical key for Plex server names."""
    return (name or "").strip().casefold()

def normalize_email(email: Optional[str]) -> Optional[str]:
    """Lowercase/trim emails; return None for blank/missing."""
    if not email:
        return None
    e = email.strip()
    return e.lower() if e else None

def safe_lower(value: Optional[str]) -> str:
    """Lowercase without blowing up on None."""
    return (value or "").lower()

def safe_strip(value: Optional[str]) -> str:
    return (value or "").strip()
