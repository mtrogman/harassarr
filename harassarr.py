# harassarr.py
import logging
import sys
import os
import argparse
from datetime import datetime, timedelta
import mysql.connector
from modules import dbFunctions, configFunctions, plexFunctions, validateFunctions, emailFunctions

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
configFile = "./config/config.yml"


def checkInactiveUsersOnPlex(configFile):
    try:
        # Load database configuration
        db_config = configFunctions.getConfig(configFile)['database']

        # Load Plex configurations
        plex_configs = [config for config in configFunctions.getConfig(configFile) if config.startswith('PLEX-')]

        for plex_config_name in plex_configs:
            plex_config = configFunctions.getConfig(configFile)[plex_config_name]

            # Get Inactive users from the database for the specific server
            inactive_users = dbFunctions.getUsersByStatus(
                user=db_config['user'],
                password=db_config['password'],
                host=db_config['host'],
                database=db_config['database'],
                status='Inactive',
                server_name=plex_config['serverName']
            )

            # Get the list of Plex users for the specific server
            plex_users = plexFunctions.listPlexUsers(
                baseUrl=plex_config['baseUrl'],
                token=plex_config['token'],
                serverName=plex_config['serverName'],
                standardLibraries=plex_config['standardLibraries'],
                optionalLibraries=plex_config['optionalLibraries']
            )

            # Check for Inactive Plex users in the database
            for user in inactive_users:
                primary_email = user["primaryEmail"].lower()

                # Check if the user is still on the Plex server
                if any(plex_user["Email"].lower() == primary_email for plex_user in plex_users):
                    logging.warning(
                        f"Inactive user '{primary_email}' on server '{plex_config['serverName']}' still has access to the Plex server."
                    )

                    # Invoke removePlexUser
                    shared_libraries = plex_config['standardLibraries'] + plex_config['optionalLibraries']
                    plexFunctions.removePlexUser(configFile, plex_config['serverName'], primary_email, shared_libraries)

    except Exception as e:
        logging.error(f"Error checking inactive users on Plex server: {e}")


def checkPlexUsersNotInDatabase(configFile):
    try:
        # Load database configuration
        db_config = configFunctions.getConfig(configFile)['database']

        # Load Plex configurations
        plex_configs = [config for config in configFunctions.getConfig(configFile) if config.startswith('PLEX-')]

        for plex_config_name in plex_configs:
            plex_config = configFunctions.getConfig(configFile)[plex_config_name]

            # Get the list of Plex users for the specific server
            plex_users = plexFunctions.listPlexUsers(
                baseUrl=plex_config['baseUrl'],
                token=plex_config['token'],
                serverName=plex_config['serverName'],
                standardLibraries=plex_config['standardLibraries'],
                optionalLibraries=plex_config['optionalLibraries']
            )

            # Check for Plex users not in the database for the specific server
            # Check for Plex users not in the database for the specific server
            for plex_user in plex_users:
                primary_email = plex_user["Email"].lower()
                server_name = plex_user["Server"]

                # Check if the user's server matches the Plex configuration server name
                if plex_user["Server"].lower() == plex_config['serverName'].lower():
                    # Check if the user is in the database
                    if not dbFunctions.userExists(
                            user=db_config['user'],
                            password=db_config['password'],
                            server=db_config['host'],
                            database=db_config['database'],
                            primary_email=primary_email,
                            server_name=server_name
                    ):
                        logging.warning(
                            f"Plex user '{plex_user['Username']}' with email '{plex_user['Email']}' on server '{plex_user['Server']}' has access but is not in the database.")
                        sharedLibraries = plex_config['standardLibraries'] + plex_config['optionalLibraries']

                        # Check if the user has status 'Inactive' in the database
                        if dbFunctions.getUserStatus(
                                user=db_config['user'],
                                password=db_config['password'],
                                server=db_config['host'],
                                database=db_config['database'],
                                primary_email=primary_email,
                                server_name=server_name
                        ) == 'Inactive':
                            logging.warning(
                                f"Plex user '{plex_user['Username']}' with email '{plex_user['Email']}' on server '{plex_user['Server']}' has status 'Inactive' but is still on the Plex server.")
                            plexFunctions.removePlexUser(configFile, server_name, primary_email, sharedLibraries)

    except Exception as e:
        logging.error(f"Error checking Plex users not in the database: {e}")


def checkUsersEndDate(configFile):
    try:
        # Load database configuration
        db_config = configFunctions.getConfig(configFile)['database']

        # Connect to the database
        connection = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )

        # Create a cursor object
        cursor = connection.cursor(dictionary=True)  # Use dictionary cursor to fetch results as dictionaries

        # Query to select all active users
        query = "SELECT * FROM users WHERE status = 'Active'"
        cursor.execute(query)

        # Fetch all active users
        users = cursor.fetchall()

        # Get current date
        today = datetime.now().date()

        # Iterate through active users
        for user in users:
            # Extract relevant information using column names
            primaryEmail = user['primaryEmail']
            primaryDiscord = user['primaryDiscord']
            endDate = user['endDate']
            serverName = user['server']

            # Check if endDate is within 7 days
            if endDate is not None:
                days_left = (endDate - today).days
                # Retrieve the matching Plex configuration from config.yml
                plex_config_key = f'PLEX-{serverName}'
                plex_config = configFunctions.getConfig(configFile).get(plex_config_key, None)

                if plex_config:
                    # Log information about the user
                    if days_left < 8:
                        # Check if endDate is in the past
                        if days_left < 0:
                            sharedLibraries = plex_config['standardLibraries'] + plex_config['optionalLibraries']
                            plexFunctions.removePlexUser(configFile, serverName, primaryEmail, sharedLibraries)
                        else:
                            logging.info(f"User with primaryEmail: {primaryEmail}, primaryDiscord: {primaryDiscord} has {days_left} days left.")
                            # Determine which email(s) to use based on notifyEmail value
                            notifyEmail = dbFunctions.getNotifyEmail(configFile, serverName, primaryEmail)
                            if notifyEmail == 'Primary':
                                toEmail = [dbFunctions.getPrimaryEmail(configFile, serverName, primaryEmail)]
                            elif notifyEmail == 'Secondary':
                                toEmail = [dbFunctions.getSecondaryEmail(configFile, serverName, primaryEmail)]
                            elif notifyEmail == 'Both':
                                primary_email = dbFunctions.getPrimaryEmail(configFile, serverName, primaryEmail)
                                secondary_email = dbFunctions.getSecondaryEmail(configFile, serverName, primaryEmail)
                                toEmail = [primary_email, secondary_email]
                            else:
                                # Don't send an email if notifyEmail is 'None'
                                toEmail = None

                            emailFunctions.send_subscription_reminder(configFile, toEmail, primaryEmail, days_left)

        # Close the cursor and connection
        cursor.close()
        connection.close()

    except mysql.connector.Error as e:
        logging.error(f"Error checking users' endDate: {e}")



def main():
    parser = argparse.ArgumentParser(description='Harassarr Script')
    parser.add_argument('-add', metavar='service', help='Add a service (e.g., plex)')

    args = parser.parse_args()

    # Validate Configuration is good
    configFunctions.checkConfig(configFile)
    logging.info(f"Database portion of configuration file (config.yml) looks good")
    config = configFunctions.getConfig(configFile)
    host = config['database']['host']
    port = config['database']['port']
    database = config['database']['database']
    user = config['database']['user']
    password = config['database']['password']
    table = "users"

    # Validate Connection to Database is good
    dbErrorFlag = False
    serverValidation = validateFunctions.validateServer(host, port)
    if not serverValidation:
        logging.error(f"Server {host} is NOT listening on {port}")
        dbErrorFlag = True
    databaseValidation = validateFunctions.validateDBConnection(user, password, host, database)
    if not databaseValidation:
        logging.error(f"Unable to authenticated with {user} to {host}")
        dbErrorFlag = True
    validateDBDatabase = validateFunctions.validateDBDatabase(user, password, host, database)
    if not validateDBDatabase:
        logging.error(f"Database {database} does not exists on {host}")
        dbErrorFlag = True
    tableValidation = validateFunctions.validateDBTable(user, password, host, database, table)
    if not tableValidation:
        logging.error(f"Table {table} does not exists on {database}")
        dbErrorFlag = True

    # If unable to connect fully to the DB then force check/update values within config
    if dbErrorFlag:
        configFunctions.updateDatabaseConfig(configFile)

    # Check number of users in users table
    dbUsersCount = dbFunctions.countDBUsers(user, password, host, database)
    if dbUsersCount == 0:
        dbUserAddResponse = validateFunctions.getValidatedInput("Would you like to import users? (Yes or No): ",r'(?i)^(yes|no)$')
        if dbUserAddResponse.lower() == 'yes':
            while True:
                path = input("Enter path to CSV: ")

                # Validate .csv file exists in that location
                if os.path.exists(path) and path.lower().endswith('.csv'):
                    userInjection = dbFunctions.injectUsersFromCSV(user, password, host, database, path)
                    break
                else:
                    print("Invalid file path or file format. Please provide a valid path to a .csv file.")

    # Extract PLEX configurations
    plexConfigurations = [
        config[key] for key in config if key.startswith('PLEX-')
    ]

    # Check if there are any PLEX configurations
    if len(plexConfigurations) == 0:
        logging.info("No valid PLEX configurations found in the config file. Creating PLEX configuration.")
        while True:
            plexFunctions.createPlexConfig(configFile)
            anotherPlexConfigResponse = validateFunctions.getValidatedInput("Would you like to configure another Plex server? (Yes or No): ", r'(?i)^(yes|no)$')
            if anotherPlexConfigResponse.lower() == 'no':
                break


    else:
        logging.info("PLEX configuration(s) found in the config file (config.yml).")

        for config in plexConfigurations:
            baseUrl = config.get("baseUrl")
            token = config.get("token")
            serverName = config.get("serverName")
            standardLibraries = config.get("standardLibraries")
            optionalLibraries = config.get("optionalLibraries")

            if baseUrl and token:
                plexValidation = validateFunctions.validatePlex(baseUrl, token)
                if plexValidation:
                    logging.info(f"Successfully connected to Plex instance: {serverName}")
            else:
                logging.warning(f"Skipping invalid PLEX configuration entry: {config}")
            # logic to add additional plex servers
            if args.add and args.add.lower() == 'plex':
                logging.info("Adding Additional Plex configuration(s).")
                plexFunctions.createPlexConfig(configFile)
                return

            plexUserInfo = plexFunctions.listPlexUsers(baseUrl, token, serverName, standardLibraries, optionalLibraries)

    # See if there are any sneaky people who should not be on the plex servers (and boot em if there are)
    checkPlexUsersNotInDatabase(configFile)

    # See if anyone with an inactive status is still somehow on plex server
    checkInactiveUsersOnPlex(configFile)

    # Check for users with less than 7 days left or subscription has lapsed.
    checkUsersEndDate(configFile)


if __name__ == "__main__":
    main()
