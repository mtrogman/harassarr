# harassarr.py
import logging
import sys
import os
import argparse
import discord
from discord.ext import commands
from datetime import datetime
import mysql.connector
from modules import dbFunctions, configFunctions, plexFunctions, validateFunctions, emailFunctions, discordFunctions

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
configFile = "./config/config.yml"


def checkInactiveUsersOnPlex(configFile):
    try:
        # Load database configuration
        dbConfig = configFunctions.getConfig(configFile)['database']

        # Load Plex configurations
        plexConfigs = [config for config in configFunctions.getConfig(configFile) if config.startswith('PLEX-')]

        for plexConfigName in plexConfigs:
            plexConfig = configFunctions.getConfig(configFile)[plexConfigName]

            # Get Inactive users from the database for the specific server
            inactiveUsers = dbFunctions.getUsersByStatus(
                user=dbConfig['user'],
                password=dbConfig['password'],
                host=dbConfig['host'],
                database=dbConfig['database'],
                status='Inactive',
                serverName=plexConfig['serverName']
            )

            # Get the list of Plex users for the specific server
            plexUsers = plexFunctions.listPlexUsers(
                baseUrl=plexConfig['baseUrl'],
                token=plexConfig['token'],
                serverName=plexConfig['serverName'],
                standardLibraries=plexConfig['standardLibraries'],
                optionalLibraries=plexConfig['optionalLibraries']
            )

            # Check for Inactive Plex users in the database
            for user in inactiveUsers:
                primaryEmail = user["primaryEmail"].lower()

                # Check if the user is still on the Plex server
                if any(plexUser["Email"].lower() == primaryEmail for plexUser in plexUsers):
                    logging.warning(
                        f"Inactive user '{primaryEmail}' on server '{plexConfig['serverName']}' still has access to the Plex server."
                    )

                    # Invoke removePlexUser
                    sharedLibraries = plexConfig['standardLibraries'] + plexConfig['optionalLibraries']
                    plexFunctions.removePlexUser(configFile, plexConfig['serverName'], primaryEmail, sharedLibraries)

    except Exception as e:
        logging.error(f"Error checking inactive users on Plex server: {e}")


def checkPlexUsersNotInDatabase(configFile):
    try:
        # Load database configuration
        dbConfig = configFunctions.getConfig(configFile)['database']

        # Load Plex configurations
        plexConfigs = [config for config in configFunctions.getConfig(configFile) if config.startswith('PLEX-')]

        for plexConfigName in plexConfigs:
            plexConfig = configFunctions.getConfig(configFile)[plexConfigName]

            # Get the list of Plex users for the specific server
            plexUsers = plexFunctions.listPlexUsers(
                baseUrl=plexConfig['baseUrl'],
                token=plexConfig['token'],
                serverName=plexConfig['serverName'],
                standardLibraries=plexConfig['standardLibraries'],
                optionalLibraries=plexConfig['optionalLibraries']
            )

            # Check for Plex users not in the database for the specific server
            # Check for Plex users not in the database for the specific server
            for plexUser in plexUsers:
                primaryEmail = plexUser["Email"].lower()
                serverName = plexUser["Server"]

                # Check if the user's server matches the Plex configuration server name
                if plexUser["Server"].lower() == plexConfig['serverName'].lower():
                    # Check if the user is in the database
                    if not dbFunctions.userExists(
                            user=dbConfig['user'],
                            password=dbConfig['password'],
                            server=dbConfig['host'],
                            database=dbConfig['database'],
                            primaryEmail=primaryEmail,
                            serverName=serverName
                    ):
                        logging.warning(
                            f"Plex user '{plexUser['Username']}' with email '{plexUser['Email']}' on server '{plexUser['Server']}' has access but is not in the database.")
                        sharedLibraries = plexConfig['standardLibraries'] + plexConfig['optionalLibraries']

                        # Check if the user has status 'Inactive' in the database
                        if dbFunctions.getUserStatus(
                                user=dbConfig['user'],
                                password=dbConfig['password'],
                                server=dbConfig['host'],
                                database=dbConfig['database'],
                                primaryEmail=primaryEmail,
                                serverName=serverName
                        ) == 'Inactive':
                            logging.warning(
                                f"Plex user '{plexUser['Username']}' with email '{plexUser['Email']}' on server '{plexUser['Server']}' has status 'Inactive' but is still on the Plex server.")
                            plexFunctions.removePlexUser(configFile, serverName, primaryEmail, sharedLibraries)

    except Exception as e:
        logging.error(f"Error checking Plex users not in the database: {e}")


def checkUsersEndDate(configFile):
    try:
        # Load database configuration
        dbConfig = configFunctions.getConfig(configFile)['database']

        # Connect to the database
        connection = mysql.connector.connect(
            host=dbConfig['host'],
            user=dbConfig['user'],
            password=dbConfig['password'],
            database=dbConfig['database']
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
                daysLeft = (endDate - today).days
                # Retrieve the matching Plex configuration from config.yml
                plexConfigKey = f'PLEX-{serverName}'
                plexConfig = configFunctions.getConfig(configFile).get(plexConfigKey, None)

                if plexConfig:
                    # Log information about the user
                    if daysLeft < 8:
                        # Check if endDate is in the past
                        logging.info(f"User with primaryEmail: {primaryEmail}, primaryDiscord: {primaryDiscord} has {daysLeft} days left.")

                        if daysLeft < 0:
                            sharedLibraries = plexConfig['standardLibraries'] + plexConfig['optionalLibraries']
                            plexFunctions.removePlexUser(configFile, serverName, primaryEmail, sharedLibraries)
                        else:
                            # Determine which email(s) to use based on notifyEmail value
                            notifyEmail = dbFunctions.getDBField(configFile, serverName, primaryEmail)
                            if notifyEmail == 'Primary':
                                toEmail = [dbFunctions.getDBField(configFile, serverName, primaryEmail)]
                            elif notifyEmail == 'Secondary':
                                toEmail = [dbFunctions.getDBField(configFile, serverName, primaryEmail)]
                            elif notifyEmail == 'Both':
                                primaryEmail = dbFunctions.getDBField(configFile, serverName, primaryEmail)
                                secondaryEmail = dbFunctions.getDBField(configFile, serverName, primaryEmail)
                                toEmail = [primaryEmail, secondaryEmail]
                            else:
                                # Don't send an email if notifyEmail is 'None'
                                toEmail = None

                            notifyDiscord = dbFunctions.getDBField(configFile, serverName, primaryEmail)
                            if notifyDiscord == 'Primary':
                                toDiscord = [dbFunctions.getDBField(configFile, serverName, primaryEmail)]
                            elif notifyDiscord == 'Secondary':
                                toDiscord = [dbFunctions.getDBField(configFile, serverName, primaryEmail)]
                            elif notifyDiscord == 'Both':
                                primaryDiscord = dbFunctions.getDBField(configFile, serverName, primaryEmail)
                                secondaryDiscord = dbFunctions.getDBField(configFile, serverName, primaryEmail)
                                toDiscord = [primaryDiscord, secondaryDiscord]
                            else:
                                # Don't send an email if notifyEmail is 'None'
                                toDiscord = None

                            # emailFunctions.sendSubscriptionReminder(configFile, toEmail, primaryEmail, daysLeft)
                            # discordFunctions.sendDiscordSubscriptionReminder(configFile, toDiscord, primaryEmail, daysLeft)

        # Close the cursor and connection
        cursor.close()
        connection.close()

    except mysql.connector.Error as e:
        logging.error(f"Error checking users' endDate: {e}")










def main():
    parser = argparse.ArgumentParser(description='Harassarr Script')
    parser.add_argument('-add', metavar='service', help='Add a service (e.g., plex)')

    args = parser.parse_args()
    config = configFunctions.getConfig(configFile)
    # Validate Configuration is good
    configFunctions.checkConfig(configFile)
    logging.info(f"Database configuration looks good")
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
    else:
        logging.info(f"Sucessfully connected to database")

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

    # # See if there are any sneaky people who should not be on the plex servers (and boot em if there are)
    # checkPlexUsersNotInDatabase(configFile)

    # # See if anyone with an inactive status is still somehow on plex server
    # checkInactiveUsersOnPlex(configFile)

    # # Check for users with less than 7 days left or subscription has lapsed.
    # checkUsersEndDate(configFile)


if __name__ == "__main__":
    main()
