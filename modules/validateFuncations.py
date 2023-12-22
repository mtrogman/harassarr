# plexFunctions.py
import sys
import logging
import socket
import mysql.connector
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


def validateDBConnection(user, password, server):
    try:
        cnx = mysql.connector.connect(user=user, password=password, host=server)
        if cnx:
            cnx.close()
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


def get_validated_input(prompt, pattern):
    user_input = input(prompt)
    if user_input != '':
        return validate_input(user_input, pattern)
    else:
        return None

def validate_input(input_string, pattern):
    while input_string is not None and not re.match(pattern, input_string):
        logging.warning("Invalid input. Please try again.")
        input_string = input()
    return input_string