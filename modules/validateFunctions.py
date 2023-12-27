# plexFunctions.py
import sys
import logging
import socket
import mysql.connector
from plexapi.server import PlexServer
import re


logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def validateServer(server, port):
    try:
        # Try connecting to the server on the specified port
        with socket.create_connection((server, port), timeout=1):
            pass
        return True
    except (socket.timeout, socket.error):
        return False


def validateDBConnection(user, password, server, database):
    try:
        with mysql.connector.connect(user=user, password=password, host=server, database=database) as cnx:
            pass
        return True
    except mysql.connector.Error as err:
        logging.error(f"Error: {err}")
        return False


def validateDBDatabase(user, password, server, database):
    try:
        cnx = mysql.connector.connect(user=user, password=password, host=server)
        cursor = cnx.cursor()

        cursor.execute(f"SHOW DATABASES LIKE '{database}';")
        result = cursor.fetchone()

        cursor.close()
        cnx.close()

        return bool(result)

    except mysql.connector.Error as err:
        logging.error(f"Error: {err}")
        return False


def validateDBTable(user, password, server, database, table):
    try:
        cnx = mysql.connector.connect(user=user, password=password, host=server, database=database)
        cursor = cnx.cursor()

        cursor.execute(f"SHOW TABLES FROM {database} LIKE '{table}';")
        result = cursor.fetchone()

        cursor.close()
        cnx.close()

        return bool(result)

    except mysql.connector.Error as err:
        logging.error(f"Error: {err}")
        return False


def getValidatedInput(prompt, pattern):
    user_input = input(prompt)
    if user_input != '':
        return validateInput(user_input, pattern)
    else:
        return None


def validateInput(input_string, pattern):
    while input_string is not None and not re.match(pattern, input_string):
        logging.warning("Invalid input. Please try again.")
        input_string = input()
    return input_string


def validatePlex(base_url, token):
    try:
        plex = PlexServer(base_url, token)
        if plex:
            # Logged into plex
            return True
    except Exception as e:
        # probably rate limited.
        logging.error(f"Error with plex login. Please check Plex authentication details.")
        logging.error(f"If you have restarted the bot multiple times recently, this is most likely due to being ratelimited on the Plex API. Try again in 10 minutes.")
        logging.error(f'Error: {e}')
        return False