#configFunctions.py
import os
import yaml
import mysql.connector
import logging
import sys
import socket
import re
import modules.dbFunctions as dbFunctions


logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def getConfig(file):
    with open(file, 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config


def checkConfig(configFile):
    default_config = {
        'database': {
            'host': 'localhost',
            'port': '3306',
            'database': 'media_mgmt',
            'user': 'lsql_harassarr',
            'password': '',
        }
    }

    # Check if config file exists, if not, create it with an empty dictionary
    if not os.path.isfile(configFile):
        with open(configFile, 'w') as file:
            yaml.dump(default_config, file)
        logging.info(f"{configFile} did not exist. Creating...")
        createDatabaseConfig(configFile)
    config = getConfig(configFile)

    # Check if 'database' key exists, if not, add it with default values
    if 'database' not in config:
        logging.info("Database configuration not found in config.yml.")
        config.update(default_config)
        with open(configFile, 'w') as file:
            yaml.dump(config, file)
        return False

    required_keys = ['user', 'password', 'host', 'database', 'port']

    # Check if all required keys exist in config['database'], and provide defaults if missing
    if not all(key in config['database'] for key in required_keys):
        logging.info("Invalid or incomplete database configuration in config.yml.")
        for key in required_keys:
            config['database'][key] = config['database'].get(key, '')
        with open(configFile, 'w') as file:
            yaml.dump(config, file)
        uDBCresponse = updateDatabaseConfig(configFile)
        if uDBCresponse:
            return True
        else:
            return False

    return True


def createDatabaseConfig(configFile):
    server = get_validated_input("Enter IP address or hostname of database: ", r'^[a-zA-Z0-9.-]+$')
    port = get_validated_input("Enter port utilized by the database (default is 3306): ", r'^[a-zA-Z0-9.-]+$') or '3306'

    if not validateServer(server, port):
        while True:
            logging.error(
                f"Could not connect to the database on port {port}. Please enter a valid IP address or hostname.")
            server = get_validated_input("Enter IP address or hostname of database: ", r'^[a-zA-Z0-9.-]+$')
            port = get_validated_input("Enter port utilized by the database (default is 3306): ", r'^[a-zA-Z0-9.-]+$') or '3306'

            if validateServer(server, port):
                break

    root_user = input("Enter root database user (default is root): ") or 'root'
    root_password = input("Enter root database password: ")

    while True:
        try:
            cnx = mysql.connector.connect(user=root_user, password=root_password, host=server)
            cnx.close()
            break
        except mysql.connector.Error as e:
            logging.error(f"Could not connect to the database with the provided credentials. Error: {e}")
            logging.error("Please enter valid credentials.")
            root_user = input("Enter root database user (default is root): ") or 'root'
            root_password = input("Enter root database password: ")

    new_user = input("Enter new username (default is lsql_harassarr): ") or 'lsql_harassarr'
    new_password = input("Enter new user password: ")
    database = input("Enter database name (default is media_mgmt): ") or 'media_mgmt'
    createDBStructure = dbFunctions.createDBStructure(root_user, root_password, database, server)
    createDBUser = dbFunctions.createDBUser(root_user, root_password, new_user, new_password, database, server)
    if createDBStructure:
        if createDBUser:
            config = getConfig(configFile)
            config['database'].update({
                'user': new_user,
                'password': new_password,
                'host': server,
                'port': port,
                'table': database
            })

            with open(configFile, 'w') as config_file:
                yaml.dump(config, config_file)

            return True
        else:
            return False
    else:
        return False


def updateDatabaseConfig(configFile):
    config = getConfig(configFile)
    server = config['database'].get('host', '')
    port = config['database'].get('port', 3306)
    database = config['database'].get('database', '')
    user = config['database'].get('user', '')
    password = config['database'].get('password', '')

    # Validate Server is a database and listening on expected port
    server = input(f"Confirm this is where the database is hosted (Current: {server}): ")
    port = input(f"Confirm this is the port used by the database (Current: {port}): ")
    if not validateServer(server, port):
        while True:
            logging.error(f"Could not connect to the database on port 3306. Please enter a valid IP address or hostname.")
            server = get_validated_input("Enter IP address or hostname of database: ", r'^[a-zA-Z0-9.-]+$')
            port = get_validated_input("Enter the port used by the database: ", r'^[a-zA-Z0-9.-]+$')

            if validateServer(server, port):
                break
    port = int(port)
    # Validate user and password are correct and can login to db
    user = input(f"Enter new user (current user is {user}): ") or user
    password = input(f"Enter new password (current password is {password}): ") or password
    cnx = mysql.connector.connect(user=user, password=password, host=server)
    if cnx:
        cnx.close()
    else:
        while True:
            logging.error(f"Could not connect to the database with the credentials provided.  Please enter valid creds.")
            user = input(f"Enter new user (current user is {user}): ") or user
            password = input(f"Enter new password (current password is {password}): ") or password
            cnx = mysql.connector.connect(user=user, password=password, host=server)
            if cnx:
                cnx.close()
                break
            else:
                logging.error(f"Could not connect to the database with the credentials provided.  Please enter valid creds.")
    # Validate the database and table exist
    try:
        cnx = mysql.connector.connect(user=user, password=password, host=server, database=database)
        cursor = cnx.cursor()

        # Check if the database exists
        cursor.execute("SELECT DATABASE();")
        current_database = cursor.fetchone()[0]

        # Close the cursor and connection
        cursor.close()
        cnx.close()

    except mysql.connector.Error as err:
        logging.error(f"Error: {err}")
        return False
    database = input(f"Enter database (default is {database}): ") or database

    config = getConfig(configFile)
    config['database'].update({
        'user': user,
        'password': password,
        'host': server,
        'port': port,
        'database': database
    })

    with open(configFile, 'w') as config_file:
        yaml.dump(config, config_file)

    return True


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
    user_input = validate_input(user_input, pattern)
    return user_input


def validate_input(input_string, pattern):
    while not re.match(pattern, input_string):
        logging.info(f"Invalid input. Please try again.")
        input_string = input()
    return input_string