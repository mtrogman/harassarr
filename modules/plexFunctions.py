# modules/plexFunctions.py
import logging, sys
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer

from modules import configFunctions, emailFunctions, discordFunctions, dbFunctions

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def _db_user_exists(configFile: str, serverName: str, primaryEmail: str) -> bool:
    cfg = configFunctions.getConfig(configFile)['database']
    return dbFunctions.userExists(
        user=cfg['user'],
        password=cfg['password'],
        server=cfg['host'],
        database=cfg['database'],
        primaryEmail=(primaryEmail or "").lower(),
        serverName=(serverName or "").lower(),
    )



def createPlexConfig(configFile):
    username = ""
    password = ""
    serverName = ""

    while True:
        username = input(f"Enter Plex user (Default: {username}): ") or username
        password = input(f"Enter Plex password (Default: {password}): ") or password
        serverName = input(f"Enter Plex server name (Friendly Name) (Default: {serverName}): ") or serverName

        try:
            account = MyPlexAccount(username, password)
            plex = account.resource(serverName).connect()
            if plex:
                break
        except Exception as e:
            if str(e).startswith("(429)"):
                logging.error("Too many requests. Please try again later.")
                return
            logging.error("Could not connect to Plex server. Please check your credentials.")

    cfg = configFunctions.getConfig(configFile)
    key = "PLEX-" + serverName.replace(" ", "_")
    cfg.setdefault(key, {})

    libraries = plex.library.sections()
    print("Available Libraries:")
    for i, library in enumerate(libraries, start=1):
        print(f"{i}. {library.title}")

    selected = input("Enter the numbers of default libraries to share (comma-separated, 'all' for all): ")
    selected = selected.lower().split(',')

    selectedStandard = []
    selectedOptional = []

    if 'all' in selected:
        selectedStandard = [lib.title for lib in libraries]
    else:
        for n in selected:
            try:
                idx = int(n.strip()) - 1
                selectedStandard.append(libraries[idx].title)
            except Exception:
                logging.warning("Invalid selection: %s", n)

    opt = input("Enter the numbers of optional (4k) libraries to share (comma-separated, 'none' for none): ")
    opt = opt.lower().split(',')
    if 'none' not in opt:
        for n in opt:
            try:
                idx = int(n.strip()) - 1
                selectedOptional.append(libraries[idx].title)
            except Exception:
                logging.warning("Invalid selection: %s", n)

    cfg[key].update({
        'baseUrl': plex._baseurl,
        'token': plex._token,
        'serverName': serverName,
        'standardLibraries': selectedStandard,
        'optionalLibraries': selectedOptional
    })

    import yaml
    with open(configFile, 'w') as f:
        yaml.dump(cfg, f)

    logging.info("Authenticated and stored token for Plex instance: %s", serverName)


def listPlexUsers(baseUrl, token, serverName, standardLibraries, optionalLibraries, **kwargs):
    plex = PlexServer(baseUrl, token)
    users = plex.myPlexAccount().users()
    userList = []
    std_count = len(standardLibraries)
    opt_count = len(optionalLibraries)

    for user in users:
        # Skip users lacking an email (local/managed accounts)
        if not getattr(user, "email", None):
            logging.warning("Skipping Plex user '%s' on '%s' (no email; likely local/managed).",
                            user.title, serverName)
            continue

        for serverInfo in user.servers:
            if serverName == serverInfo.name:
                if opt_count == 0:
                    fourK = 'No'
                elif serverInfo.numLibraries == std_count + opt_count:
                    fourK = 'Yes'
                elif serverInfo.numLibraries == std_count:
                    fourK = 'No'
                elif serverInfo.numLibraries >= std_count + opt_count:
                    fourK = 'Yes'
                    logging.warning("%s (%s) has extra libraries shared; investigate.",
                                    user.email, user.title)
                else:
                    fourK = 'No'
                    logging.warning("%s (%s) has not enough libraries shared; investigate.",
                                    user.email, user.title)

                userList.append({
                    "User ID": user.id,
                    "Username": user.title,
                    "Email": user.email,
                    "Server": serverName,
                    "Number of Libraries": serverInfo.numLibraries,
                    "All Libraries Shared": serverInfo.allLibraries,
                    "4K Libraries": fourK
                })

    return userList


# === NEW: filter actionable Plex users (skip local/no-email) ===
def actionable_from_plex(
    baseUrl: str,
    token: str,
    serverName: str,
    standardLibraries: list,
    optionalLibraries: list,
    purpose: str | None = None,
) -> list[dict]:
    """
    Returns Plex users for 'serverName' that are actionable for DB/role audits:
    - Skips local/managed users (no Email)
    - Ensures 'Server' matches serverName
    Logs a summary like: "Assembled N users after filters on 'X' (for Y)."
    """
    try:
        users = listPlexUsers(
            baseUrl=baseUrl,
            token=token,
            serverName=serverName,
            standardLibraries=standardLibraries,
            optionalLibraries=optionalLibraries,
        )
    except Exception as e:
        logging.error("Error listing Plex users for '%s': %s", serverName, e)
        return []

    filtered = []
    for u in users or []:
        email = (u.get("Email") or "").strip()
        srv = u.get("Server")
        if not email:
            logging.warning("Skipping Plex user '%s' on '%s' (no email; likely local/managed).",
                            u.get("Username"), serverName)
            continue
        if srv != serverName:
            continue
        filtered.append(u)

    logging.info("Assembled %d users after filters on '%s' (for %s).",
                 len(filtered), serverName, (purpose or "audit"))
    return filtered


def removePlexUser(configFile: str, serverName: str, userEmail: str, sharedLibraries: list[str] | None = None, dryrun: bool = False) -> None:
    """
    Remove a user's access from a Plex server.
    - Always attempts to remove the Plex share/friend for `userEmail` on `serverName`.
    - Only updates the database or sends notifications if a matching DB row exists.
    - `sharedLibraries` is accepted for backward-compat/signature parity; actual removal uses account.removeFriend().
    """
    try:
        cfg = configFunctions.getConfig(configFile)
    except Exception as e:
        logging.error("Unable to read config '%s': %s", configFile, e)
        return

    # Find the PLEX-* block that matches this serverName
    plex_block = None
    for k, v in cfg.items():
        if str(k).startswith("PLEX-") and isinstance(v, dict) and v.get("serverName") == serverName:
            plex_block = v
            break
    if plex_block is None:
        logging.error("No configuration found for Plex server '%s'", serverName)
        return

    baseUrl = plex_block.get("baseUrl")
    token = plex_block.get("token")
    if not baseUrl or not token:
        logging.error("Invalid Plex configuration for '%s': baseUrl/token missing.", serverName)
        return

    # Connect to Plex
    try:
        plex = PlexServer(baseUrl, token)
    except Exception as e:
        logging.error("Failed to connect to Plex '%s': %s", serverName, e)
        return

    # --- Remove share (friend) on Plex ---
    if not userEmail:
        logging.error("Cannot remove Plex user with empty email on server '%s'.", serverName)
        return

    if dryrun:
        logging.info("[DRY-RUN] Would remove Plex user '%s' from '%s'", userEmail, serverName)
    else:
        try:
            removed = plex.myPlexAccount().removeFriend(user=userEmail)
            if removed:
                logging.info("User '%s' has been successfully removed from Plex server '%s'", userEmail, serverName)
            else:
                logging.warning("Friendship with '%s' not found and thus not removed.", userEmail)
        except Exception as e:
            logging.warning("Error removing friendship for '%s' on '%s': %s", userEmail, serverName, e)

    # --- From here on: only act if user exists in DB ---
    db_cfg = cfg.get("database", {})
    user_in_db = False
    try:
        user_in_db = dbFunctions.userExists(
            user=db_cfg.get("user"),
            password=db_cfg.get("password"),
            server=db_cfg.get("host"),
            database=db_cfg.get("database"),
            primaryEmail=(userEmail or "").lower(),
            serverName=(serverName or "").lower(),
        )
    except Exception as e:
        logging.error("DB existence check failed for %s on %s: %s", userEmail, serverName, e)

    if not user_in_db:
        logging.info("User %s not present in DB for server %s; skipped DB inactivation and notifications.", userEmail, serverName)
        return

    # Pull user-specific fields we need for templating
    try:
        # 4k flag
        fourk = dbFunctions.getDBField(configFile, serverName, userEmail, '4k') or 'No'
        # Pricing tier from config ('4k' or '1080p')
        price_block_key = '4k' if str(fourk).strip().lower() == 'yes' else '1080p'
        pricing = plex_block.get(price_block_key, {}) if isinstance(plex_block, dict) else {}
        oneM = str(pricing.get('1Month', ""))        # strings so .format works cleanly
        threeM = str(pricing.get('3Month', ""))
        sixM = str(pricing.get('6Month', ""))
        twelveM = str(pricing.get('12Month', ""))

        # streams (same simple heuristic as before)
        server_name_tail = (serverName or "").strip()
        try:
            streamCount = int(server_name_tail[-1]) if server_name_tail and server_name_tail[-1].isdigit() else 2
        except Exception:
            streamCount = 2

        # days_left from DB endDate
        endDate = dbFunctions.getDBField(configFile, serverName, userEmail, 'endDate')
        from datetime import datetime, date
        today = date.today()
        days_left = 0
        if endDate:
            try:
                if isinstance(endDate, datetime):
                    days_left = (endDate.date() - today).days
                else:
                    dt = datetime.strptime(str(endDate), "%Y-%m-%d").date()
                    days_left = (dt - today).days
            except Exception:
                days_left = 0

        # Determine email recipients
        toEmails = None
        try:
            notifyEmail = dbFunctions.getDBField(configFile, serverName, userEmail, 'notifyEmail')
            if notifyEmail == 'Primary':
                toEmails = [dbFunctions.getDBField(configFile, serverName, userEmail, 'primaryEmail')]
            elif notifyEmail == 'Secondary':
                toEmails = [dbFunctions.getDBField(configFile, serverName, userEmail, 'secondaryEmail')]
            elif notifyEmail == 'Both':
                p = dbFunctions.getDBField(configFile, serverName, userEmail, 'primaryEmail')
                s = dbFunctions.getDBField(configFile, serverName, userEmail, 'secondaryEmail')
                toEmails = [e for e in (p, s) if e]
        except Exception as e:
            logging.error("Failed to compute email recipients for %s on %s: %s", userEmail, serverName, e)

        # Determine Discord recipients
        toDiscord = None
        try:
            notifyDiscord = dbFunctions.getDBField(configFile, serverName, userEmail, 'notifyDiscord')
            if notifyDiscord == 'Primary':
                toDiscord = [dbFunctions.getDBField(configFile, serverName, userEmail, 'primaryDiscordId')]
            elif notifyDiscord == 'Secondary':
                toDiscord = [dbFunctions.getDBField(configFile, serverName, userEmail, 'secondaryDiscordId')]
            elif notifyDiscord == 'Both':
                pD = dbFunctions.getDBField(configFile, serverName, userEmail, 'primaryDiscordId')
                sD = dbFunctions.getDBField(configFile, serverName, userEmail, 'secondaryDiscordId')
                toDiscord = [d for d in (pD, sD) if d]
        except Exception as e:
            logging.error("Failed to compute Discord recipients for %s on %s: %s", userEmail, serverName, e)

        # Send notifications (email + Discord) with full pricing context
        try:
            emailFunctions.sendSubscriptionRemoved(
                configFile=configFile,
                toEmails=toEmails,
                primaryEmail=userEmail,
                days_left=days_left,
                fourk=fourk,
                streamCount=streamCount,
                oneM=oneM, threeM=threeM, sixM=sixM, twelveM=twelveM,
                dryrun=dryrun
            )
        except Exception as e:
            logging.error("Error notifying user '%s' via email for Plex server '%s': %s", userEmail, serverName, e)

        try:
            discordFunctions.sendSubscriptionRemoved(
                configFile=configFile,
                toDiscordIds=toDiscord,
                primaryEmail=userEmail,
                daysLeft=days_left,
                fourk=fourk,
                streamCount=streamCount,
                oneM=oneM, threeM=threeM, sixM=sixM, twelveM=twelveM,
                dryrun=dryrun
            )
        except Exception as e:
            logging.error("Error notifying user '%s' on Discord for Plex server '%s': %s", userEmail, serverName, e)

        # Update DB status to Inactive
        if dryrun:
            logging.info("SETTING USER (%s) TO INACTIVE SKIPPED DUE TO DRYRUN", userEmail)
        else:
            try:
                dbFunctions.updateUserStatus(configFile, serverName, userEmail, 'Inactive')
                logging.info("User '%s' status updated to 'Inactive' for server '%s'.", userEmail, serverName)
            except Exception as e:
                logging.error("Failed to update DB status for %s on %s: %s", userEmail, serverName, e)

    except Exception as e:
        logging.error("Removal post-processing failed for %s on %s: %s", userEmail, serverName, e)
