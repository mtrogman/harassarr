# harassarr.py
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta

import discord
import mysql.connector
import schedule

from modules import (
    dbFunctions,
    configFunctions,
    plexFunctions,
    validateFunctions,
    emailFunctions,
    discordFunctions,
)


CONFIG_FILE = os.getenv("HARASSARR_CONFIG", "/config/config.yml")
LOG_FILE = os.getenv("HARASSARR_LOG", "/config/harassarr.log")

# ----- logging -----
if not os.path.exists(LOG_FILE):
    open(LOG_FILE, "w").close()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_FILE)],
)

def _safe_lower(s): return (s or "").lower()
def _norm(s): return (s or "").strip()

# ---- log retention ----
try:
    _cfg_tmp = configFunctions.getConfig(CONFIG_FILE)
    LOG_RETENTION_DAYS = _cfg_tmp.get("log", {}).get("retention", 90)
except Exception:
    LOG_RETENTION_DAYS = 90

def _delete_old_logs(path, retention_days):
    try:
        with open(path, "r+", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            f.seek(0)
            for line in lines:
                try:
                    stamp = line.split(" - ", 1)[0]
                    dt = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S,%f")
                    if datetime.now() - dt <= timedelta(days=retention_days):
                        f.write(line)
                except Exception:
                    f.write(line)
            f.truncate()
    except Exception:
        pass

_delete_old_logs(LOG_FILE, LOG_RETENTION_DAYS)

# ========= STRICT pricing helpers =========

def _format_money(v):
    if v is None: return ""
    try:
        return f"${float(str(v)):,.2f}"
    except Exception:
        return str(v)

def _resolve_plex_cfg_strict(full_cfg: dict, server_name: str) -> dict | None:
    key = f"PLEX-{server_name}"
    return full_cfg.get(key)

def _extract_prices_from_cfg(full_cfg: dict, server_name: str, fourk_flag: str):
    plex_cfg = _resolve_plex_cfg_strict(full_cfg, server_name)
    if plex_cfg is None:
        # IMPORTANT: caller will decide to skip notifying/removal if block is missing
        return None, "", "", "", ""
    tier_key = "4k" if _safe_lower(fourk_flag) == "yes" else "1080p"
    tier = plex_cfg.get(tier_key)
    if not isinstance(tier, dict):
        return plex_cfg, "", "", "", ""
    return plex_cfg, _format_money(tier.get("1Month")), _format_money(tier.get("3Month")), _format_money(tier.get("6Month")), _format_money(tier.get("12Month"))

# ========= Discord role audit (HTTP-only; no gateway) =========

async def _ids_with_role_async(token: str, guild_id: int, role_name: str, ids_to_check: set[str]) -> set[str]:
    """
    HTTP-only: login, use REST (fetch_guild, fetch_roles, fetch_member), close; no gateway.
    """
    intents = discord.Intents.none()
    client = discord.Client(intents=intents)
    have = set()
    try:
        await client.login(token)

        guild = await client.fetch_guild(guild_id)
        if not guild:
            logging.error("Discord: bot not in guild %s", guild_id)
            return have

        roles = await guild.fetch_roles()
        target = next((r for r in roles if r.name.lower() == role_name.lower()), None)
        if not target:
            logging.warning("Discord: role '%s' not found in guild %s", role_name, guild_id)
            return have

        for sid in ids_to_check:
            try:
                m = await guild.fetch_member(int(sid))
            except Exception:
                m = None
            if m and any(rr.id == target.id for rr in m.roles):
                have.add(sid)
        return have
    finally:
        try:
            await client.close()
        except Exception:
            pass

def _ids_with_role(config_path: str, role_name: str, ids: list[str]) -> set[str]:
    cfg = configFunctions.getConfig(config_path)
    dcfg = cfg.get("discord", {})
    token = dcfg.get("token")
    guild_id = dcfg.get("guildId")
    if not token or not guild_id:
        logging.error("Discord token/guildId missing; cannot verify roles.")
        return set()
    try:
        gid = int(guild_id)
    except Exception:
        logging.error("Discord guildId must be an integer; got %r", guild_id)
        return set()
    ids_set = {str(i) for i in ids if i}
    if not ids_set:
        return set()
    try:
        return asyncio.run(_ids_with_role_async(token, gid, role_name, ids_set))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(_ids_with_role_async(token, gid, role_name, ids_set))
        finally:
            loop.close()

# ========= Checks =========

def checkInactiveUsersOnDiscord(config_path, dryrun):
    try:
        cfg = configFunctions.getConfig(config_path)
        dbConf = cfg["database"]
        plexConfs = [cfg[k] for k in cfg if str(k).startswith("PLEX-")]

        for pc in plexConfs:
            server = pc.get("serverName")
            role_name = pc.get("role")
            if not server or not role_name:
                logging.warning("Discord audit: missing serverName/role in PLEX block; skipping.")
                continue

            inactive = dbFunctions.getUsersByStatus(
                user=dbConf["user"], password=dbConf["password"], host=dbConf["host"],
                database=dbConf["database"], status="Inactive", serverName=server
            )
            active = dbFunctions.getUsersByStatus(
                user=dbConf["user"], password=dbConf["password"], host=dbConf["host"],
                database=dbConf["database"], status="Active", serverName=server
            )

            active_ids = { _norm(u.get("primaryDiscordId")) for u in active if u.get("primaryDiscordId") } | \
                         { _norm(u.get("secondaryDiscordId")) for u in active if u.get("secondaryDiscordId") }

            candidates = []
            for u in inactive:
                for key in ("primaryDiscordId","secondaryDiscordId"):
                    did = _norm(u.get(key))
                    if did and did not in active_ids:
                        candidates.append(did)

            if not candidates:
                logging.info("Discord audit '%s': no inactive users with Discord IDs to check.", server)
                continue

            still_has = _ids_with_role(config_path, role_name, candidates)
            logging.info("Discord audit '%s': candidates=%d, still_has_role=%d", server, len(candidates), len(still_has))

            for did in still_has:
                try:
                    discordFunctions.removeRole(config_path, did, role_name, dryrun=dryrun)
                except Exception as e:
                    logging.error("Failed to remove Discord role '%s' from %s: %s", role_name, did, e)

    except Exception as e:
        logging.error("Error in checkInactiveUsersOnDiscord: %s", e)

def _actionable_plex_users(pc: dict, purpose: str) -> list[dict]:
    return plexFunctions.actionable_from_plex(
        baseUrl=pc["baseUrl"],
        token=pc["token"],
        serverName=pc["serverName"],
        standardLibraries=pc.get("standardLibraries", []),
        optionalLibraries=pc.get("optionalLibraries", []),
        purpose=purpose,
    )

def checkPlexUsersNotInDatabase(config_path, dryrun):
    try:
        cfg = configFunctions.getConfig(config_path)
        dbConf = cfg["database"]
        plexConfs = [cfg[k] for k in cfg if str(k).startswith("PLEX-")]

        for pc in plexConfs:
            server_cfg_name = pc["serverName"]
            plex_users = _actionable_plex_users(pc, purpose="DB presence audit")

            for pu in plex_users:
                email = pu.get("Email")
                server_from_plex = pu.get("Server")
                if not email or not server_from_plex:
                    continue

                in_db = dbFunctions.userExists(
                    user=dbConf["user"], password=dbConf["password"],
                    server=dbConf["host"], database=dbConf["database"],
                    primaryEmail=_safe_lower(email), serverName=_safe_lower(server_from_plex)
                )
                if not in_db:
                    logging.info(
                        "[DRY-RUN] Would remove Plex user '%s' from '%s' (not in DB)" if dryrun
                        else "Removing Plex user '%s' from '%s' (not in DB)",
                        email, server_cfg_name
                    )
                    try:
                        shared = pc.get("standardLibraries", []) + pc.get("optionalLibraries", [])
                        plexFunctions.removePlexUser(config_path, server_cfg_name, _safe_lower(email), shared, dryrun=dryrun)
                    except Exception as e:
                        logging.error("Error removing '%s' from Plex '%s': %s", email, server_cfg_name, e)

    except Exception as e:
        logging.error("Error in checkPlexUsersNotInDatabase: %s", e)

def checkInactiveUsersOnPlex(config_path, dryrun):
    try:
        cfg = configFunctions.getConfig(config_path)
        dbConf = cfg["database"]
        plexConfs = [cfg[k] for k in cfg if str(k).startswith("PLEX-")]

        for pc in plexConfs:
            server = pc["serverName"]
            plex_users = _actionable_plex_users(pc, purpose="inactive audit")

            inactive = dbFunctions.getUsersByStatus(
                user=dbConf["user"], password=dbConf["password"], host=dbConf["host"],
                database=dbConf["database"], status="Inactive", serverName=server
            )
            plex_emails = { _safe_lower(u.get("Email")) for u in plex_users if u.get("Email") }

            for u in inactive:
                pEmail = u.get("primaryEmail")
                if not pEmail:
                    logging.error("Inactive DB user missing primaryEmail: %s", u)
                    continue
                if _safe_lower(pEmail) in plex_emails:
                    logging.warning("Inactive user '%s' on server '%s' still has Plex access.", pEmail, server)
                    try:
                        shared = pc.get("standardLibraries", []) + pc.get("optionalLibraries", [])
                        plexFunctions.removePlexUser(CONFIG_FILE, server, _safe_lower(pEmail), shared, dryrun=dryrun)
                    except Exception as e:
                        logging.error("Error removing user '%s' from Plex '%s': %s", pEmail, server, e)

    except Exception as e:
        logging.error("Error checking inactive users on Plex server: %s", e)

def checkUsersEndDate(config_path, dryrun):
    try:
        cfg = configFunctions.getConfig(config_path)
        db = cfg["database"]

        con = mysql.connector.connect(
            host=db["host"], user=db["user"], password=db["password"], database=db["database"]
        )
        cur = con.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE status = 'Active'")
        users = cur.fetchall()
        today = datetime.now().date()

        for u in users:
            endDate = u.get("endDate")
            if endDate is None:
                continue

            primaryEmail = u.get("primaryEmail")
            primaryDiscord = u.get("primaryDiscord")
            serverName = u.get("server")
            fourk = u.get("4k")

            try:
                streamCount = int(str(serverName)[-1])
            except Exception:
                streamCount = 2

            daysLeft = (endDate - today).days
            if daysLeft >= 8:
                continue

            logging.info(
                "User with primaryEmail: %s, primaryDiscord: %s has %d days left.",
                primaryEmail, primaryDiscord, daysLeft
            )

            plex_cfg, oneM, threeM, sixM, twelveM = _extract_prices_from_cfg(cfg, serverName, fourk)
            if plex_cfg is None:
                logging.info(
                    "Skipping notifications for %s: user is on unconfigured Plex server '%s'.",
                    primaryEmail, serverName
                )
                continue

            if daysLeft < 0:
                shared = plex_cfg.get("standardLibraries", []) + plex_cfg.get("optionalLibraries", [])
                try:
                    if dryrun:
                        logging.info("[DRY-RUN] Would remove expired Plex user %s on server %s", primaryEmail, serverName)
                    else:
                        plexFunctions.removePlexUser(config_path, serverName, primaryEmail, shared, dryrun=False)
                except Exception as e:
                    logging.error("Error removing expired user %s on server %s: %s", primaryEmail, serverName, e)
                continue

            # targets
            toEmail = []
            notifyEmail = dbFunctions.getDBField(CONFIG_FILE, serverName, primaryEmail, "notifyEmail")
            if notifyEmail == "Primary":
                toEmail = [dbFunctions.getDBField(CONFIG_FILE, serverName, primaryEmail, "primaryEmail")]
            elif notifyEmail == "Secondary":
                toEmail = [dbFunctions.getDBField(CONFIG_FILE, serverName, primaryEmail, "secondaryEmail")]
            elif notifyEmail == "Both":
                pE = dbFunctions.getDBField(CONFIG_FILE, serverName, primaryEmail, "primaryEmail")
                sE = dbFunctions.getDBField(CONFIG_FILE, serverName, primaryEmail, "secondaryEmail")
                toEmail = [e for e in (pE, sE) if e]

            toDiscord = []
            notifyDiscord = dbFunctions.getDBField(CONFIG_FILE, serverName, primaryEmail, "notifyDiscord")
            if notifyDiscord == "Primary":
                toDiscord = [dbFunctions.getDBField(CONFIG_FILE, serverName, primaryEmail, "primaryDiscordId")]
            elif notifyDiscord == "Secondary":
                toDiscord = [dbFunctions.getDBField(CONFIG_FILE, serverName, primaryEmail, "secondaryDiscordId")]
            elif notifyDiscord == "Both":
                pD = dbFunctions.getDBField(CONFIG_FILE, serverName, primaryEmail, "primaryDiscordId")
                sD = dbFunctions.getDBField(CONFIG_FILE, serverName, primaryEmail, "secondaryDiscordId")
                toDiscord = [d for d in (pD, sD) if d]

            # send
            try:
                emailFunctions.sendSubscriptionReminder(
                    CONFIG_FILE, toEmail, primaryEmail, daysLeft, fourk, streamCount,
                    oneM, threeM, sixM, twelveM, dryrun=dryrun
                )
            except Exception as e:
                logging.error("Email notify failed for %s: %s", primaryEmail, e)

            try:
                discordFunctions.sendDiscordSubscriptionReminder(
                    CONFIG_FILE, toDiscord, primaryEmail, daysLeft, fourk, streamCount,
                    oneM, threeM, sixM, twelveM, dryrun=dryrun
                )
            except Exception as e:
                logging.error("Discord notify failed for %s: %s", primaryEmail, e)

        cur.close()
        con.close()

    except mysql.connector.Error as e:
        logging.error("Error checking users' endDate: %s", e)

# ========= Orchestration =========

def dailyRun(args, dryrun):
    logging.info("Starting Daily Run")
    configFunctions.checkConfig(CONFIG_FILE)
    cfg = configFunctions.getConfig(CONFIG_FILE)
    logging.info("Configuration file loaded successfully")

    host = cfg["database"]["host"]
    port = cfg["database"]["port"]
    database = cfg["database"]["database"]
    user = cfg["database"]["user"]
    password = cfg["database"]["password"]
    table = "users"

    if not validateFunctions.validateServer(host, port):
        logging.error("Database server %s is NOT listening on port %s.", host, port)
        sys.exit(1)
    if not validateFunctions.validateDBConnection(user, password, host, database):
        logging.error("Unable to authenticate user %s to database server %s.", user, host)
        sys.exit(1)
    if not validateFunctions.validateDBDatabase(user, password, host, database):
        logging.error("Database %s does not exist on %s.", database, host)
        sys.exit(1)
    if not validateFunctions.validateDBTable(user, password, host, database, table):
        logging.error("Table %s does not exist in database %s.", table, database)
        sys.exit(1)

    logging.info("Database connection validated successfully. Proceeding with checks.")

    plexConfs = [cfg[k] for k in cfg if str(k).startswith("PLEX-")]
    if not plexConfs:
        logging.error("No valid Plex configurations found in the config file. Exiting.")
        sys.exit(1)

    for pc in plexConfs:
        baseUrl = pc.get("baseUrl")
        token = pc.get("token")
        serverName = pc.get("serverName")
        if not baseUrl or not token:
            logging.error("Invalid Plex configuration for server %s. Missing baseUrl or token.", serverName)
            continue
        if not validateFunctions.validatePlex(baseUrl, token):
            logging.error("Unable to connect to Plex instance %s. Check baseUrl and token.", serverName)
            continue
        logging.info("Successfully connected to Plex instance: %s", serverName)

    # Run checks (log-and-continue on errors)
    try:
        checkPlexUsersNotInDatabase(CONFIG_FILE, dryrun=dryrun)
    except Exception as e:
        logging.error("checkPlexUsersNotInDatabase error: %s", e)
    try:
        checkInactiveUsersOnPlex(CONFIG_FILE, dryrun=dryrun)
    except Exception as e:
        logging.error("checkInactiveUsersOnPlex error: %s", e)
    try:
        checkUsersEndDate(CONFIG_FILE, dryrun=dryrun)
    except Exception as e:
        logging.error("checkUsersEndDate error: %s", e)
    try:
        checkInactiveUsersOnDiscord(CONFIG_FILE, dryrun=dryrun)
    except Exception as e:
        logging.error("checkInactiveUsersOnDiscord error: %s", e)

    logging.info("Daily Run completed successfully.")

def main():
    parser = argparse.ArgumentParser(description="Harassarr Script")
    parser.add_argument("-add", metavar="service", help="Add a service (e.g., plex)")
    parser.add_argument("--dryrun", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--dry-run", action="store_true", dest="dryrun2", help="Run in dry-run mode")
    parser.add_argument("-time", metavar="time", type=str, default=os.getenv("TIME", ""), help="HH:MM daily run time")
    parser.add_argument("--run-now", action="store_true", help="Run immediately once")

    args = parser.parse_args()
    dryrun = bool(args.dryrun or args.dryrun2)
    logging.info("CLI parsed: dryrun=%s, run_now=%s, time=%s", dryrun, bool(args.run_now), args.time or "(none)")

    # schedule logic
    if args.run_now:
        dailyRun(args, dryrun=dryrun)
        if not args.time:
            sys.exit(0)

    if not args.time and not args.run_now:
        dailyRun(args, dryrun=dryrun)
        sys.exit(0)

    try:
        run_time = datetime.strptime(args.time, "%H:%M").time()
    except ValueError:
        print("Error: Invalid time format. Use HH:MM.")
        sys.exit(1)

    logging.info("Starting Daily Run at %s", run_time)
    schedule.every().day.at(str(run_time)).do(dailyRun, args, dryrun=dryrun)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
