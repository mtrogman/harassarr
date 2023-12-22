# plexFunctions.py
import sys
import logging
import yaml
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
import modules.validateFuncations as validateFunctions
import modules.configFunctions as configFunctions


logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def createPlexConfig(configFile):
    username = ""
    password = ""
    serverName = ""
    while True:
        username = input(f"Enter plex user (Default: {username}): ") or username
        password = input(f"Enter plex password (Default: {password}): ") or password
        serverName = input(f"Enter the plex server name (Friendly Name) (Default: {serverName}): ") or serverName

        try:
            account = MyPlexAccount(username, password)
            plex = account.resource(serverName).connect()
            if plex:
                break
        except Exception as e:
            if str(e).startswith("(429)"):
                logging.error(f"Too many requests. Please try again later.")
                return
            logging.error(f"Could not connect to Plex server. Please check your credentials.")

    config = configFunctions.getConfig(configFile)
    formattedServerName = "PLEX-" + serverName.replace(" ", "_")
    config.setdefault(formattedServerName, {})

    config[formattedServerName].update({
        'base_url': plex._baseurl,
        'token': plex._token,
        'server_name': serverName
    })
    with open(configFile, 'w') as config_file:
        yaml.dump(config, config_file)
    logging.info(f"Authenticated and Stored token for Plex instance: {serverName}")


def listPlexUsers(configFile):
    config = configFunctions.getConfig(configFile)
    server = config['database'].get('host', '')
    plex = PlexServer(PLEX_BASE_URL, PLEX_TOKEN)
