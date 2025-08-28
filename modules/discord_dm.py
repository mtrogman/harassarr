from __future__ import annotations
import asyncio
import contextlib
import logging
from typing import Optional

import discord


class DiscordDM:
    """
    Minimal, DM-only client.
    - Connect once per run
    - send_dm() logs 50007 and returns False (no retries)
    - close() cleans up to avoid "Unclosed connector"
    """
    def __init__(self, token: str, logger: logging.Logger):
        self._token = token
        self._logger = logger
        self._ready = asyncio.Event()
        intents = discord.Intents.none()
        self._client = discord.Client(intents=intents)

        @self._client.event
        async def on_ready():
            self._logger.info("Discord connected as %s", self._client.user)
            self._ready.set()

    async def start(self, timeout: int = 30):
        asyncio.create_task(self._client.start(self._token))
        await asyncio.wait_for(self._ready.wait(), timeout=timeout)

    async def close(self):
        with contextlib.suppress(Exception):
            await self._client.close()

    async def send_dm(self, discord_user_id: int, content: str) -> bool:
        try:
            user = await self._client.fetch_user(int(discord_user_id))
            await user.send(content)
            return True
        except discord.errors.Forbidden as e:
            # 50007: Cannot send messages to this user (DMs disabled)
            self._logger.warning("DM blocked for %s: %s", discord_user_id, e)
            return False
        except discord.errors.HTTPException as e:
            self._logger.error("Discord HTTP error to %s: %s", discord_user_id, e)
            return False
