# plexFunctions.py
import sys, logging, yaml
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
import modules.configFunctions as configFunctions
import modules.emailFunctions as emailFunctions
import modules.discordFunctions as discordFunctions
import modules.dbFunctions as dbFunctions


logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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

    config = configFunctions.getConfig(configFile)
    formattedServerName = "PLEX-" + serverName.replace(" ", "_")
    config.setdefault(formattedServerName, {})

    # List available libraries and let the user choose
    libraries = plex.library.sections()
    print("Available Libraries:")
    for i, library in enumerate(libraries, start=1):
        print(f"{i}. {library.title}")

    selectedLibraries = input("Enter the numbers of default libraries to share (comma-separated, 'all' for all): ")
    selectedLibraries = selectedLibraries.lower().split(',')

    selectedStandardLibraries = []
    selectedOptionalLibraries = []

    if 'all' in selectedLibraries:
        selectedStandardLibraries = [library.title for library in libraries]
    else:
        for selection in selectedLibraries:
            try:
                selection = int(selection.strip())
                libraryTitle = libraries[selection - 1].title
                selectedStandardLibraries.append(libraryTitle)
            except (ValueError, IndexError):
                logging.warning(f"Invalid selection: {selection}")

    # Ask for optional libraries
    optionalLibraries = input("Enter the numbers of optional (4k) libraries to share (comma-separated, 'none' for none): ")
    optionalLibraries = optionalLibraries.lower().split(',')

    if 'none' not in optionalLibraries:
        for selection in optionalLibraries:
            try:
                selection = int(selection.strip())
                libraryTitle = libraries[selection - 1].title
                selectedOptionalLibraries.append(libraryTitle)
            except (ValueError, IndexError):
                logging.warning(f"Invalid selection: {selection}")

    config[formattedServerName].update({
        'baseUrl': plex._baseurl,
        'token': plex._token,
        'serverName': serverName,
        'standardLibraries': selectedStandardLibraries,
        'optionalLibraries': selectedOptionalLibraries
    })

    with open(configFile, 'w') as config_file:
        yaml.dump(config, config_file)

    logging.info(f"Authenticated and stored token for Plex instance: {serverName}")


def listPlexUsers(baseUrl, token, serverName, standardLibraries, optionalLibraries, **kwargs):
    plex = PlexServer(baseUrl, token)
    users = plex.myPlexAccount().users()
    userList = []
    standardLibraries = len(standardLibraries)
    optionalLibraries = len(optionalLibraries)

    for user in users:
        for serverInfo in user.servers:
            if serverName == serverInfo.name:
                if optionalLibraries == 0:
                    fourK = 'No'
                elif serverInfo.numLibraries == standardLibraries + optionalLibraries:
                    fourK = 'Yes'
                elif serverInfo.numLibraries == standardLibraries:
                    fourK = 'No'
                elif serverInfo.numLibraries >= standardLibraries + optionalLibraries:
                    fourK = 'Yes'
                    logging.warning(f"{user.email} ({user.title}) has extra libraries shared to them; you should investigate.")
                else:
                    fourK = 'No'
                    logging.warning(f"{user.email} ({user.title}) has not enough libraries shared to them; you should investigate")
                userInfo = {
                    "User ID": user.id,
                    "Username": user.title,
                    "Email": user.email,
                    "Server": serverName,
                    "Number of Libraries": serverInfo.numLibraries,
                    "All Libraries Shared": serverInfo.allLibraries,
                    "4K Libraries": fourK
                }
                userList.append(userInfo)

    return userList

def removePlexUser(configFile, serverName, userEmail, sharedLibraries, dryrun):
    # Load the YAML config using getConfig
    config = configFunctions.getConfig(configFile)

    try:
        # Retrieve the matching Plex configuration from config.yml
        plexConfig = config.get(f'PLEX-{serverName}', None)
        if not isinstance(plexConfig, dict):
            logging.error(f"No configuration found for Plex server '{serverName}'")
            return

        # Get the actual configuration directly
        baseUrl = plexConfig.get('baseUrl', None)
        token = plexConfig.get('token', None)
        if not baseUrl or not token:
            logging.error(f"Invalid configuration for Plex server '{serverName}'")
            return

        # Authenticate to Plex
        plex = PlexServer(baseUrl, token)
    except Exception as e:
        logging.error(f"Error authenticating to Plex server '{serverName}': {e}")
        return

    try:
        # If --dryrun then skips this functionality
        if dryrun:
            logging.info(f"REMOVE USER ({userEmail} SKIPPED DUE TO DRYRUN")
        else:
            # Update user settings to remove all shared library sections
            removeLibraries = plex.myPlexAccount().updateFriend(user=userEmail, sections=sharedLibraries, server=plex, removeSections=True)
            if removeLibraries:
                logging.info(f"User '{userEmail}' has been successfully removed from Plex server '{serverName}'")

    except Exception as e:
        logging.error(f"Error removing user '{userEmail}' from Plex server '{serverName}': {e}")
    
        # Determine which email(s) to use based on notifyEmail value
        notifyEmail = dbFunctions.getDBField(configFile, serverName, userEmail, 'notifyEmail')
        if notifyEmail == 'Primary':
            toEmail = [dbFunctions.getDBField(configFile, serverName, userEmail, 'primaryEmail')]
        elif notifyEmail == 'Secondary':
            toEmail = [dbFunctions.getDBField(configFile, serverName, userEmail, 'secondaryEmail')]
        elif notifyEmail == 'Both':
            primaryEmail = dbFunctions.getDBField(configFile, serverName, userEmail, 'primaryEmail')
            secondaryEmail = dbFunctions.getDBField(configFile, serverName, userEmail, 'secondaryEmail')
            toEmail = [primaryEmail, secondaryEmail]
        else:
            # Don't send an email if notifyEmail is 'None'
            toEmail = None

        notifyDiscord = dbFunctions.getDBField(configFile, serverName, userEmail, 'notifyDiscord')
        if notifyDiscord == 'Primary':
            toDiscord = [dbFunctions.getDBField(configFile, serverName, userEmail, 'primaryDiscordId')]
        elif notifyDiscord == 'Secondary':
            toDiscord = [dbFunctions.getDBField(configFile, serverName, userEmail, 'secondaryDiscordId')]
        elif notifyDiscord == 'Both':
            primaryDiscord = dbFunctions.getDBField(configFile, serverName, userEmail, 'primaryDiscordId')
            secondaryDiscord = dbFunctions.getDBField(configFile, serverName, userEmail, 'secondaryDiscordId')
            toDiscord = [primaryDiscord, secondaryDiscord]
        else:
            # Don't send an email if notifyDiscord is 'None'
            toDiscord = None

        streamCount = int(serverName[-1]) if serverName and serverName[-1].isdigit() else None
        fourk = dbFunctions.getDBField(configFile, serverName, userEmail, '4k')

        is4kSubscribed = plexConfig.get('fourk', 'no') == 'yes'
        pricing = plexConfig['4k' if is4kSubscribed else '1080p']

        # Set pricing values or None if they don't exist
        oneM = pricing.get('1Month', None)
        threeM = pricing.get('3Month', None)
        sixM = pricing.get('6Month', None)
        twelveM = pricing.get('12Month', None)
    try:
        emailFunctions.sendSubscriptionRemoved(configFile, toEmail, userEmail, streamCount, fourk, oneM, threeM, sixM, twelveM, dryrun=dryrun)
        discordFunctions.sendDiscordSubscriptionRemoved(configFile, toDiscord, userEmail, streamCount, fourk, oneM, threeM, sixM, twelveM, dryrun=dryrun)


    except Exception as e:
        logging.error(f"Error notifying user '{userEmail}' from their subscription on Plex server '{serverName}': {e}")


    try:
        # logging.info(f"REMOVE FRIEND TEMPORARILY DISABLED DURING TESTING")
        removalFriend = plex.myPlexAccount().removeFriend(user=userEmail)
        if removalFriend:
            logging.info(f"User '{userEmail}' has been successfully removed from Plex server '{serverName}'")
        else:
            logging.warning(f"Friendship with '{userEmail}' not found and thus not removed.")

    except Exception as e:
        logging.warning(f"Error removing friendship from user '{userEmail}' from Plex server '{serverName}': {e}")

    # If --dryrun then skips this functionality
    if dryrun:
        logging.info(f"SETTING USER ({userEmail} TO INACTIVE SKIPPED DUE TO DRYRUN")
    else:
        # Update user status to 'Inactive'
        dbFunctions.updateUserStatus(configFile, serverName, userEmail, 'Inactive')
