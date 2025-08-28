# modules/discord_notify.py
from __future__ import annotations
import logging
from typing import Optional, Dict, Any

import discord

from modules.snapshot import SnapshotLog

logger = logging.getLogger(__name__)

async def safe_dm(
    discord_client: discord.Client,
    user_id: int,
    content: str,
    snapshot: SnapshotLog,
    *,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Send a DM, but don't explode on 50007 (user has DMs closed).
    Logs once per attempt and records the attempt in the snapshot.
    """
    ctx = context or {}
    dm_attempted = True
    dm_sent = False
    try:
        user_obj = await discord_client.fetch_user(user_id)
        await user_obj.send(content)
        dm_sent = True
        return True
    except discord.Forbidden as e:
        # Includes error code 50007: "Cannot send messages to this user"
        logger.warning("Discord DM blocked for user_id=%s: %s", user_id, str(e))
        return False
    except discord.HTTPException as e:
        logger.error("Discord DM HTTP error for user_id=%s: %s", user_id, str(e))
        return False
    finally:
        snapshot.add(
            user_id=str(ctx.get("user_id") or user_id),
            username=ctx.get("username"),
            email=ctx.get("email"),
            server=ctx.get("server"),
            days_left=ctx.get("days_left"),
            dm_attempted=dm_attempted,
            dm_sent=dm_sent,
        )
