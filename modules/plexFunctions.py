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
    username = input("Enter plex user: ")
    password = input("Enter plex password: ")
    serverName = input("Enter the plex server name (Friendly Name): ")

    try:
        account = MyPlexAccount(username, password)
        plex = account.resource(serverName).connect()
    except Exception as e:
        if str(e).startswith("(429)"):
            logging.error(f"Too many requests. Please try again later.")
            return

        logging.error(f"Could not connect to Plex server. Please check your credentials.")
        return


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


def listPlexUsers(configFile):
    config = configFunctions.getConfig(configFile)
    server = config['database'].get('host', '')
    plex = PlexServer(PLEX_BASE_URL, PLEX_TOKEN)
