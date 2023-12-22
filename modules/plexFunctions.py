# plexFunctions.py
import sys
import logging
import yaml
import re
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
from plexapi.library import MovieSection, ShowSection

import modules.validateFuncations as validateFunctions
import modules.configFunctions as configFunctions


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


def listPlexUsers(baseUrl, token, serverName, standardLibraries, optionalLibraries):
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






