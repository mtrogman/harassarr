# configFunctions.py
import os
import yaml
import mysql.connector
import logging
import sys
import modules.dbFunctions as dbFunctions
import modules.validateFunctions as validateFunctions

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def getConfig(file):
    try:
        with open(file, 'r') as yaml_file:
            config = yaml.safe_load(yaml_file) or {}
        return config
    except yaml.YAMLError as e:
        logging.error(f"Error loading YAML from {file}: {e}")
        return {}


def checkConfig(configFile):
    if not os.path.isfile(configFile):
        with open(configFile, 'w') as file:
            yaml.dump({}, file)
        logging.info(f"{configFile} did not exist. Creating...")
        createDatabaseConfig(configFile)
    config = getConfig(configFile)

    if 'database' not in config:
        logging.info("Database configuration not found in config.yml.")
        createDatabaseConfig(configFile)

    required_keys = ['user', 'password', 'host', 'database', 'port']

    if not all(key in config['database'] for key in required_keys):
        logging.info("Invalid or incomplete database configuration in config.yml.")
        for key in required_keys:
            config['database'][key] = config['database'].get(key, '')
        with open(configFile, 'w') as file:
            yaml.dump(config, file)
        updateDatabaseConfig(configFile)


def createDatabaseConfig(configFile):
    server = validateFunctions.getValidatedInput("Enter IP address or hostname of database: ", r'^[a-zA-Z0-9.-]+$')
    port = int(validateFunctions.getValidatedInput("Enter port utilized by the database (default is 3306): ", r'^[0-9]+$') or '3306')

    if not validateFunctions.validateServer(server, port):
        while True:
            logging.error(f"Could not connect to the database on port {port}. Please enter a valid IP address or hostname.")
            server = validateFunctions.getValidatedInput("Enter IP address or hostname of database: ", r'^[a-zA-Z0-9.-]+$')
            port = int(validateFunctions.getValidatedInput("Enter port utilized by the database (default is 3306): ", r'^[0-9]+$') or '3306')

            if validateFunctions.validateServer(server, port):
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
            config['database'] = {
                'user': new_user,
                'password': new_password,
                'host': server,
                'port': port,
                'database': database
            }

            with open(configFile, 'w') as config_file:
                yaml.dump(config, config_file)
            logging.info("Database configuration updated successfully.")


def updateDatabaseConfig(configFile):
    config = getConfig(configFile)
    server = config['database'].get('host', '')
    port = config['database'].get('port', 3306)
    database = config['database'].get('database', '')
    user = config['database'].get('user', '')
    password = config['database'].get('password', '')

    server = validateFunctions.getValidatedInput(f"Confirm this is where the database is hosted (Current: {server}): ") or server
    port = int(validateFunctions.getValidatedInput(f"Confirm this is the port used by the database (Current: {port}): ") or port)

    if not validateFunctions.validateServer(server, port):
        while True:
            logging.error(f"Could not connect to the database on port {port}. Please enter a valid IP address or hostname.")
            server = validateFunctions.getValidatedInput("Enter IP address or hostname of database: ", r'^[a-zA-Z0-9.-]+$')
            port = int(validateFunctions.getValidatedInput("Enter port utilized by the database (default is 3306): ", r'^[0-9]+$') or '3306')

            if validateFunctions.validateServer(server, port):
                break

    while True:
        user = validateFunctions.getValidatedInput(f"Enter new user (current user is {user}): ") or user
        password = validateFunctions.getValidatedInput(f"Enter new password (current password is {password}): ") or password
        database = validateFunctions.getValidatedInput(f"Enter new database (current database is {database}): ") or database

        try:
            cnx = mysql.connector.connect(user=user, password=password, host=server, database=database)
            cursor = cnx.cursor()

            cursor.execute("SELECT DATABASE();")
            current_database = cursor.fetchone()[0]

            cursor.close()
            cnx.close()

            config = getConfig(configFile)
            config['database'] = {
                'user': user,
                'password': password,
                'host': server,
                'port': port,
                'database': database
            }

            with open(configFile, 'w') as config_file:
                yaml.dump(config, config_file)
            logging.info("Database configuration updated successfully.")
            break

        except mysql.connector.Error as err:
            logging.error(f"Error: {err}")
            logging.error("Database configuration update failed. Please check the provided details.")

    return True
