# modules/discordFunctions.py
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Iterable, Awaitable, Callable

import discord

from modules import configFunctions

RUN_CACHE = Path("./run_cache.json")


# ----------------- small run cache for DM-blocked flags -----------------
def _load_cache() -> dict:
    try:
        if RUN_CACHE.exists():
            return json.loads(RUN_CACHE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _save_cache(d: dict) -> None:
    try:
        RUN_CACHE.write_text(json.dumps(d, indent=2), encoding="utf-8")
    except Exception:
        pass

def _mark_dm_blocked(user_id: str) -> None:
    d = _load_cache()
    dm = d.get("dm_blocked", {})
    dm[str(user_id)] = True
    d["dm_blocked"] = dm
    _save_cache(d)


# ----------------- config helpers -----------------
def _discord_cfg(configFile: str) -> dict:
    cfg = configFunctions.getConfig(configFile)
    d = cfg.get("discord", {}) if isinstance(cfg, dict) else {}
    return {
        "token": d.get("token"),
        "guild_id": d.get("guildId"),
        "reminderSubject": d.get("reminderSubject"),
        "reminderBody": d.get("reminderBody"),
        "removalSubject": d.get("removalSubject"),
        "removalBody": d.get("removalBody"),
    }


# ----------------- bootstrap runner (simple & safe) -----------------
class _Runner(discord.Client):
    def __init__(self, intents: discord.Intents, runner: Callable[[discord.Client], Awaitable[None]]):
        super().__init__(intents=intents)
        self._runner = runner

    async def on_ready(self):
        try:
            await self._runner(self)
        except Exception as e:
            logging.error("Discord runner error: %s", e)
        finally:
            # Close gracefully after our work is done
            try:
                await self.close()
            except Exception:
                pass


def _run_client(token: str, intents: discord.Intents, runner: Callable[[discord.Client], Awaitable[None]]) -> None:
    """
    Start a short-lived discord.py client, run `runner(client)` after ready,
    then return. We set reconnect=False to avoid close-races.
    """
    async def main():
        client = _Runner(intents=intents, runner=runner)
        await client.start(token, reconnect=False)

    # Own the event loop for this short run
    asyncio.run(main())


# ----------------- templates -----------------
def _render(tpl: str, ctx: dict) -> str:
    try:
        return tpl.format_map(ctx)
    except Exception as e:
        logging.error("Discord template render failed: %s", e)
        return tpl

def _ctx(primaryEmail: str, daysLeft: int, fourk: str, streamCount: int,
         oneM: str, threeM: str, sixM: str, twelveM: str) -> dict:
    return {
        "primaryEmail": primaryEmail,
        "daysLeft": daysLeft,
        "fourk": fourk,
        "streamCount": streamCount,
        "oneM": oneM or "",
        "threeM": threeM or "",
        "sixM": sixM or "",
        "twelveM": twelveM or "",
    }


# ----------------- public API -----------------
def sendDiscordSubscriptionReminder(
    configFile: str,
    toDiscordIds: list[str] | None,
    primaryEmail: str,
    daysLeft: int,
    fourk: str,
    streamCount: int,
    oneM: str, threeM: str, sixM: str, twelveM: str,
    dryrun: bool = False
) -> None:
    if not toDiscordIds:
        return

    cfg = _discord_cfg(configFile)
    token = cfg.get("token")
    if not token:
        logging.error("Discord token missing in config; cannot send DMs.")
        return

    subj, body = cfg.get("reminderSubject"), cfg.get("reminderBody")
    if not subj or not body:
        logging.error("Discord reminder templates missing in config: discord.reminderSubject/body")
        return

    ctx = _ctx(primaryEmail, daysLeft, fourk, streamCount, oneM, threeM, sixM, twelveM)
    content = f"{_render(subj, ctx)}\n{_render(body, ctx)}"

    if dryrun:
        logging.info("[DRY-RUN] Would DM Discord IDs %s for %s (daysLeft=%s)", toDiscordIds, primaryEmail, daysLeft)
        return

    intents = discord.Intents.none()  # minimal intents for DMs

    async def runner(client: discord.Client):
        for uid in toDiscordIds:
            if not uid:
                continue
            try:
                user = await client.fetch_user(int(uid))
                dm = await user.create_dm()
                await dm.send(content)
            except discord.Forbidden as e:
                # code 50007: "Cannot send messages to this user"
                if getattr(e, "code", None) == 50007 or "Cannot send messages to this user" in str(e):
                    logging.warning("Discord: DMs disabled for user_id=%s (50007).", uid)
                    _mark_dm_blocked(str(uid))
                else:
                    logging.error("Discord Forbidden sending DM to %s: %s", uid, e)
            except Exception as e:
                logging.error("Discord error sending DM to %s: %s", uid, e)

    _run_client(token, intents, runner)


def sendSubscriptionRemoved(
    configFile: str,
    toDiscordIds: list[str] | None,
    primaryEmail: str,
    daysLeft: int,
    fourk: str,
    streamCount: int,
    oneM: str, threeM: str, sixM: str, twelveM: str,
    dryrun: bool = False
) -> None:
    if not toDiscordIds:
        return

    cfg = _discord_cfg(configFile)
    token = cfg.get("token")
    if not token:
        logging.error("Discord token missing in config; cannot send DMs.")
        return

    subj, body = cfg.get("removalSubject"), cfg.get("removalBody")
    if not subj or not body:
        logging.error("Discord removal templates missing in config: discord.removalSubject/body")
        return

    ctx = _ctx(primaryEmail, daysLeft, fourk, streamCount, oneM, threeM, sixM, twelveM)
    content = f"{_render(subj, ctx)}\n{_render(body, ctx)}"

    if dryrun:
        logging.info("[DRY-RUN] Would DM (removal) Discord IDs %s for %s", toDiscordIds, primaryEmail)
        return

    intents = discord.Intents.none()

    async def runner(client: discord.Client):
        for uid in toDiscordIds:
            if not uid:
                continue
            try:
                user = await client.fetch_user(int(uid))
                dm = await user.create_dm()
                await dm.send(content)
            except discord.Forbidden as e:
                if getattr(e, "code", None) == 50007 or "Cannot send messages to this user" in str(e):
                    logging.warning("Discord: DMs disabled for user_id=%s (50007).", uid)
                    _mark_dm_blocked(str(uid))
                else:
                    logging.error("Discord Forbidden sending removal DM to %s: %s", uid, e)
            except Exception as e:
                logging.error("Discord error sending removal DM to %s: %s", uid, e)

    _run_client(token, intents, runner)


def removeRole(configFile: str, discordId: str, role_name: str, dryrun: bool = False) -> None:
    cfg = _discord_cfg(configFile)
    token = cfg.get("token")
    guild_id = cfg.get("guild_id")
    if not token or not guild_id:
        logging.error("Discord token/guildId missing; cannot remove roles.")
        return

    if dryrun:
        logging.info("[DRY-RUN] Would remove role '%s' from member %s", role_name, discordId)
        return

    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True  # requires "Server Members Intent" enabled

    async def runner(client: discord.Client):
        try:
            guild = client.get_guild(int(guild_id)) or await client.fetch_guild(int(guild_id))
            if not guild:
                logging.error("Discord: bot not in guild %s", guild_id)
                return

            try:
                roles = await guild.fetch_roles()
            except AttributeError:
                roles = getattr(guild, "roles", [])
            target = next((r for r in roles if r.name.lower() == role_name.lower()), None)
            if not target:
                logging.warning("Discord: role '%s' not found in guild %s", role_name, guild_id)
                return

            try:
                member = await guild.fetch_member(int(discordId))
            except Exception:
                member = guild.get_member(int(discordId))
            if not member:
                logging.warning("Discord: member %s not found in guild %s", discordId, guild_id)
                return

            await member.remove_roles(target, reason="Harassarr: inactive user cleanup")
            logging.info("Removed role '%s' from member %s", role_name, discordId)

        except discord.Forbidden as e:
            logging.error("Discord Forbidden removing role '%s' from %s: %s", role_name, discordId, e)
        except Exception as e:
            logging.error("Discord error removing role '%s' from %s: %s", role_name, discordId, e)

    _run_client(token, intents, runner)


def members_having_role(configFile: str, role_name: str, ids: Iterable[str]) -> set[str]:
    """
    Return subset of `ids` that currently have role_name in the configured guild.
    """
    cfg = _discord_cfg(configFile)
    token = cfg.get("token")
    guild_id = cfg.get("guild_id")
    if not token or not guild_id:
        logging.error("Discord token/guildId missing; cannot verify roles.")
        return set()

    ids = {str(i) for i in ids if i}
    if not ids:
        return set()

    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True

    have: set[str] = set()

    async def runner(client: discord.Client):
        try:
            guild = client.get_guild(int(guild_id)) or await client.fetch_guild(int(guild_id))
            if not guild:
                logging.error("Discord: bot not in guild %s", guild_id)
                return

            try:
                roles = await guild.fetch_roles()
            except AttributeError:
                roles = getattr(guild, "roles", [])
            target = next((r for r in roles if r.name.lower() == role_name.lower()), None)
            if not target:
                logging.warning("Discord: role '%s' not found in guild %s", role_name, guild_id)
                return

            for sid in ids:
                member = None
                try:
                    member = await guild.fetch_member(int(sid))
                except Exception:
                    member = guild.get_member(int(sid))
                if member and any(r.id == target.id for r in getattr(member, "roles", [])):
                    have.add(sid)
        except Exception as e:
            logging.error("Discord role-audit error: %s", e)

    _run_client(token, intents, runner)
    return have
