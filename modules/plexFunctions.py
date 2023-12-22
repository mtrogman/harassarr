# plexFunctions.py
import sys
import logging
import yaml
from plexapi.myplex import MyPlexAccount
import modules.validateFuncations as validateFunctions
import modules.configFunctions as configFunctions


logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def createPlexConfig(configFile):
    username = input("Enter plex user: ") or 'TrogsPlexTrial'
    password = input("Enter plex password: ") or 'kC5G4ur9f32k83@DHQ2hQUd5'
    serverName = input("Enter the plex server name (Friendly Name): ") or 'Trog Plex Trial'

    try:
        account = MyPlexAccount(username, password)
        plex = account.resource(serverName).connect()
        print(plex)
    except Exception as e:
        if str(e).startswith("(429)"):
            logging.error(f"Too many requests. Please try again later.")
            return

        logging.error(f"Could not connect to Plex server. Please check your credentials.")
        return


    config = configFunctions.getConfig(configFile)
    config.setdefault(serverName, {})
    config[serverName].update({
        'base_url': plex._baseurl,
        'token': plex._token,
        'server_name': serverName
    })
    with open(configFile, 'w') as config_file:
        yaml.dump(config, config_file)
