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


def listPlexUsers(base_url, token, server_name):
    plex = PlexServer(base_url, token)
    users = plex.myPlexAccount().users()
    user_list = []

    for user in users:
        for server_info in user.servers:
            if server_name == server_info.name:
                user_info = {
                    "User ID": user.id,
                    "Username": user.title,
                    "Email": user.email,
                    "Server": server_name,
                    "Number of Libraries": server_info.numLibraries,
                    "All Libraries Shared": server_info.allLibraries
                }
                # Maybe i store the amount of shared libraries and if 4k is a thing
                # Or I set a flag for 4K exists or if all libraries could be shared out?
                print(user_info)
                user_list.append(user_info)

    print(len(user_list))
    return user_list


    return user_list






