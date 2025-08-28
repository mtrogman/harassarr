# modules/log_summary.py
from __future__ import annotations
import logging
from modules.snapshot import SnapshotLog

logger = logging.getLogger(__name__)

def log_run_summary(snapshot: SnapshotLog) -> None:
    s = snapshot.summary()
    logger.info(
        "Run summary: processed=%d skipped=%d dm_attempted=%d dm_sent=%d email_sent=%d removed_from_plex=%d removed_from_discord=%d",
        s["processed"], s["skipped"], s["dm_attempted"], s["dm_sent"], s["email_sent"],
        s["removed_from_plex"], s["removed_from_discord"]
    )
