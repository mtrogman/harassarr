# harassarr/modules/discord_client.py
from __future__ import annotations
import asyncio
import contextlib
import logging
from typing import Optional

import discord


class DiscordDMClient:
    """
    One client per run. Cleanly connects and closes.
    Sends DMs; if the user has DMs disabled (50007), we just log and move on.
    """
    _instance: Optional["DiscordDMClient"] = None

    def __init__(self, token: str, logger: logging.Logger):
        intents = discord.Intents.none()  # we only need DMs
        self._client = discord.Client(intents=intents)
        self._token = token
        self._logger = logger
        self._ready = asyncio.Event()

        @self._client.event
        async def on_ready():
            self._logger.info("Discord connected as %s", self._client.user)
            self._ready.set()

    @classmethod
    def instance(cls, token: str, logger: logging.Logger) -> "DiscordDMClient":
        if cls._instance is None:
            cls._instance = cls(token, logger)
        return cls._instance

    async def __aenter__(self) -> "DiscordDMClient":
        asyncio.create_task(self._client.start(self._token))
        await asyncio.wait_for(self._ready.wait(), timeout=30)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        with contextlib.suppress(Exception):
            await self._client.close()
        DiscordDMClient._instance = None

    async def send_dm(self, discord_user_id: int, content: str) -> bool:
        try:
            user = await self._client.fetch_user(int(discord_user_id))
            await user.send(content)
            return True
        except discord.errors.Forbidden as e:
            # (50007) Cannot send messages to this user
            self._logger.warning("DM blocked for %s: %s", discord_user_id, e)
            return False
        except discord.errors.HTTPException as e:
            self._logger.error("Discord HTTP error to %s: %s", discord_user_id, e)
            return False
