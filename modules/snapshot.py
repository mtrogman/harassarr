# modules/snapshot.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class UserEvent:
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    server: Optional[str] = None
    days_left: Optional[int] = None
    dm_attempted: bool = False
    dm_sent: bool = False
    email_sent: bool = False
    removed_from_plex: bool = False
    removed_from_discord: bool = False
    skipped_reason: Optional[str] = None  # e.g. "no_email", "invalid_record"

@dataclass
class SnapshotLog:
    """In-memory replacement for the old userData.csv 'snapshot'."""
    events: List[UserEvent] = field(default_factory=list)

    def add(self, **kwargs) -> None:
        self.events.append(UserEvent(**kwargs))

    def summary(self) -> Dict[str, int]:
        s = {
            "processed": 0,
            "skipped": 0,
            "dm_attempted": 0,
            "dm_sent": 0,
            "email_sent": 0,
            "removed_from_plex": 0,
            "removed_from_discord": 0,
        }
        for e in self.events:
            if e.skipped_reason:
                s["skipped"] += 1
            else:
                s["processed"] += 1
            s["dm_attempted"] += int(e.dm_attempted)
            s["dm_sent"] += int(e.dm_sent)
            s["email_sent"] += int(e.email_sent)
            s["removed_from_plex"] += int(e.removed_from_plex)
            s["removed_from_discord"] += int(e.removed_from_discord)
        return s

    def non_actionable(self) -> List[UserEvent]:
        return [e for e in self.events if e.skipped_reason]
