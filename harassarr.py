# harassarr.py
import logging
import sys
import os
import schedule
import time
import argparse
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import mysql.connector
import subprocess
from modules import dbFunctions, configFunctions, plexFunctions, validateFunctions, emailFunctions, discordFunctions

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

configFile = "/config/config.yml"
userDataFile = "/config/userData.csv"

# Set up logging to both console and file
logFile = "/config/harassarr.log"

# Check if the log file exists, create it if it doesn't
if not os.path.exists(logFile):
    open(logFile, 'w').close()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.StreamHandler(sys.stdout),
    logging.FileHandler(logFile)
])

try:
    logRetention = configFunctions.getConfig(configFile)['log']['retention']
except KeyError:
    logRetention = 90

def delete_old_logs(log_file, logRetention):
    with open(log_file, 'r+') as file:
        lines = file.readlines()
        file.seek(0)
        for line in lines:
            log_date_str = line.split(' - ', 1)[0]
            log_date = datetime.strptime(log_date_str, '%Y-%m-%d %H:%M:%S,%f')
            if datetime.now() - log_date <= timedelta(days=logRetention):
                file.write(line)
        file.truncate()

# Delete old log entries
delete_old_logs(logFile, logRetention)

def checkInactiveUsersOnDiscord(configFile, dryrun):
    # Janky way to get discord users... purge old csv, run subscript, validate csv there.
    if os.path.exists(userDataFile):
        os.remove(userDataFile)
        logging.info(f"Deleted existing userData.csv")
    else:
        logging.info(f"Cannot delete userData.csv due to it not existing")

    subprocess.run(["python", "supplemental/userDetail.py"])

    if os.path.exists(userDataFile):
        discordUserData = discordFunctions.readCsv(userDataFile)

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

                # Get Active users from the database for the specific server
                activeUsers = dbFunctions.getUsersByStatus(
                    user=dbConfig['user'],
                    password=dbConfig['password'],
                    host=dbConfig['host'],
                    database=dbConfig['database'],
                    status='Active',
                    serverName=plexConfig['serverName']
                )

                if os.path.exists(userDataFile):
                    discordUserData = discordFunctions.readCsv(userDataFile)

                # Check for Inactive Plex users in the database
                discordIds = ['primaryDiscordId', 'secondaryDiscordId']
                for user in inactiveUsers:
                    for discordId in discordIds:
                        if discordId in user:
                            DiscordID = user[discordId]

                            # Check if there is at least one active status for the primaryDiscordId
                            active_status_exists = any(u.get('primaryDiscordId') == DiscordID for u in activeUsers)

                            if not active_status_exists:
                                for user_data in discordUserData:
                                    if user_data.get('discord_id') == DiscordID:
                                        roles = user_data.get('roles')
                                        # Check if any roles in the CSV match the Plex role
                                        if plexConfig['role'].lower() in map(str.lower, roles):
                                            logging.warning(f"Inactive user '{user['primaryDiscord']}' still has {plexConfig['role']}")
                                            discordFunctions.removeRole(configFile, DiscordID, plexConfig['role'], dryrun=dryrun)
                        else:
                            logging.warning(f"Missing {discordId} key in user dictionary.")
        except Exception as e:
            logging.error(f"Error checking inactive users with Discord Roles: {e}")
    else:
        raise FileNotFoundError(f"The file {userDataFile} does not exist.")

def checkInactiveUsersOnPlex(configFile, dryrun):
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
                primaryEmail = user["primaryEmail"]

                # Ensure primaryEmail is not None
                if primaryEmail:
                    # Check if the user is still on the Plex server
                    if any(plexUser["Email"].lower() == primaryEmail.lower() for plexUser in plexUsers):
                        logging.warning(
                            f"Inactive user '{primaryEmail}' on server '{plexConfig['serverName']}' still has access to the Plex server."
                        )

                        # Invoke removePlexUser
                        sharedLibraries = plexConfig['standardLibraries'] + plexConfig['optionalLibraries']
                        plexFunctions.removePlexUser(configFile, plexConfig['serverName'], primaryEmail.lower(), sharedLibraries, dryrun=dryrun)
                else:
                    logging.error(f"Invalid user data: {user}")

    except Exception as e:
        logging.error(f"Error checking inactive users on Plex server: {e}")

def checkPlexUsersNotInDatabase(configFile, dryrun):
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
            for plexUser in plexUsers:
                primaryEmail = plexUser.get("Email")
                serverName = plexUser.get("Server")

                if primaryEmail is not None and serverName is not None:
                    # Normalize for comparison
                    primaryEmail = primaryEmail.lower()
                    serverName = serverName.lower()

                    # Check if the user's server matches the Plex configuration server name
                    if serverName == plexConfig['serverName'].lower():
                        # Check if the user is in the database
                        userExists = dbFunctions.userExists(
                            user=dbConfig['user'],
                            password=dbConfig['password'],
                            server=dbConfig['host'],
                            database=dbConfig['database'],
                            primaryEmail=primaryEmail,
                            serverName=serverName
                        )

                        if not userExists:
                            logging.warning(f"Plex user '{plexUser['Username']}' with email '{plexUser['Email']}' on server '{plexUser['Server']}' has access but is not in the database.")
                            sharedLibraries = plexConfig['standardLibraries'] + plexConfig['optionalLibraries']

                            # Remove user from Plex
                            plexFunctions.removePlexUser(configFile, serverName, primaryEmail, sharedLibraries, dryrun=dryrun)


                else:
                    logging.error(f"Invalid Plex user data: {plexUser}")
                    if dryrun:
                        logging.info(f"Dry run enabled. Skipping user removal for invalid user data: {plexUser}")
                    else:
                        # Attempt to remove if data is malformed but the user is accessible
                        plexFunctions.removePlexUser(configFile, serverName, primaryEmail, plexConfig['standardLibraries'] + plexConfig['optionalLibraries'], dryrun=dryrun)

    except Exception as e:
        logging.error(f"Error checking Plex users not in the database: {e}")

def checkUsersEndDate(configFile, dryrun):
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
            # Extract end date
            endDate = user['endDate']

            # Check if endDate is within 7 days
            if endDate is not None:
                # Extract user info
                primaryEmail = user['primaryEmail']
                primaryDiscord = user['primaryDiscord']
                serverName = user['server']
                fourk = user['4k']

                try:
                    streamCount = int(serverName[-1])
                except ValueError:
                    # Handle the case where the last character is not a number
                    streamCount = 2  # or any other default value you want to set

                daysLeft = (endDate - today).days
                # Retrieve the matching Plex configuration from config.yml
                plexConfigKey = f'PLEX-{serverName}'
                # Retrieve the matching Plex configuration from config.yml
                plexConfigs = configFunctions.getConfig(configFile)

                plexConfig = plexConfigs.get(plexConfigKey, None)

                is4kSubscribed = fourk.lower() == 'yes'
                pricing = plexConfig.get('4k' if is4kSubscribed else '1080p', None)

                # Set pricing values or None if they don't exist
                oneM = pricing.get('1Month', None)
                threeM = pricing.get('3Month', None)
                sixM = pricing.get('6Month', None)
                twelveM = pricing.get('12Month', None)

                if plexConfig:
                    # Log information about the user
                    if daysLeft < 8:
                        # Check if endDate is in the past
                        logging.info(f"User with primaryEmail: {primaryEmail}, primaryDiscord: {primaryDiscord} has {daysLeft} days left.")

                        if daysLeft < 0:
                            sharedLibraries = plexConfig['standardLibraries'] + plexConfig['optionalLibraries']
                            plexFunctions.removePlexUser(configFile, serverName, primaryEmail, sharedLibraries, dryrun=dryrun)
                        else:
                            # Determine which email(s) to use based on notifyEmail value
                            notifyEmail = dbFunctions.getDBField(configFile, serverName, primaryEmail, 'notifyEmail')
                            if notifyEmail == 'Primary':
                                toEmail = [dbFunctions.getDBField(configFile, serverName, primaryEmail, 'primaryEmail')]
                            elif notifyEmail == 'Secondary':
                                toEmail = [dbFunctions.getDBField(configFile, serverName, primaryEmail, 'secondaryEmail')]
                            elif notifyEmail == 'Both':
                                primaryEmail = dbFunctions.getDBField(configFile, serverName, primaryEmail, 'primaryEmail')
                                secondaryEmail = dbFunctions.getDBField(configFile, serverName, primaryEmail, 'secondaryEmail')
                                toEmail = [primaryEmail, secondaryEmail]
                            else:
                                # Don't send an email if notifyEmail is 'None'
                                toEmail = None

                            notifyDiscord = dbFunctions.getDBField(configFile, serverName, primaryEmail, 'notifyDiscord')
                            if notifyDiscord == 'Primary':
                                toDiscord = [dbFunctions.getDBField(configFile, serverName, primaryEmail, 'primaryDiscordId')]
                            elif notifyDiscord == 'Secondary':
                                toDiscord = [dbFunctions.getDBField(configFile, serverName, primaryEmail, 'secondaryDiscordId')]
                            elif notifyDiscord == 'Both':
                                primaryDiscord = dbFunctions.getDBField(configFile, serverName, primaryEmail, 'primaryDiscordId')
                                secondaryDiscord = dbFunctions.getDBField(configFile, serverName, primaryEmail, 'secondaryDiscordId')
                                toDiscord = [primaryDiscord, secondaryDiscord]
                            else:
                                # Don't send an email if notifyDiscord is 'None'
                                toDiscord = None

                            emailFunctions.sendSubscriptionReminder(configFile, toEmail, primaryEmail, daysLeft, fourk, streamCount, oneM, threeM, sixM, twelveM, dryrun=dryrun)
                            discordFunctions.sendDiscordSubscriptionReminder(configFile, toDiscord, primaryEmail, daysLeft, fourk, streamCount, oneM, threeM, sixM, twelveM, dryrun=dryrun)

                            discordIds = ['primaryDiscordId', 'secondaryDiscordId']

                            # Get Active users from the database for the specific server
                            activeUsers = dbFunctions.getUsersByStatus(
                                user=dbConfig['user'],
                                password=dbConfig['password'],
                                host=dbConfig['host'],
                                database=dbConfig['database'],
                                status='Active',
                                serverName=plexConfig['serverName']
                            )

                            if os.path.exists(userDataFile):
                                discordUserData = discordFunctions.readCsv(userDataFile)

                                for discordId in discordIds:
                                    if discordId in user:
                                        DiscordID = user[discordId]

                                        # Check if there is at least one active status for the primaryDiscordId
                                        active_status_exists = any(u.get('primaryDiscordId') == DiscordID for u in activeUsers)

                                        if not active_status_exists:
                                            for user_data in discordUserData:
                                                if user_data.get('discord_id') == DiscordID:
                                                    roles = user_data.get('roles')
                                                    # Check if any roles in the CSV match the Plex role
                                                    if plexConfig['role'].lower() in map(str.lower, roles):
                                                        logging.warning(f"Inactive user '{user['primaryDiscord']}' still has {plexConfig['role']}")
                                                        discordFunctions.removeRole(configFile, DiscordID, plexConfig['role'], dryrun=dryrun)
                                    else:
                                        logging.warning(f"Missing {discordId} key in user dictionary.")

        # Close the cursor and connection
        cursor.close()
        connection.close()

    except mysql.connector.Error as e:
        logging.error(f"Error checking users' endDate: {e}")

def dailyRun(args, dryrun):
    logging.info(f"Starting Daily Run")
    # Validate Configuration is good
    configFunctions.checkConfig(configFile)
    config = configFunctions.getConfig(configFile)
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
        logging.error(f"Unable to authenticate with {user} to {host}")
        dbErrorFlag = True
    validateDBDatabase = validateFunctions.validateDBDatabase(user, password, host, database)
    if not validateDBDatabase:
        logging.error(f"Database {database} does not exist on {host}")
        dbErrorFlag = True
    tableValidation = validateFunctions.validateDBTable(user, password, host, database, table)
    if not tableValidation:
        logging.error(f"Table {table} does not exist on {database}")
        dbErrorFlag = True

    # If unable to connect fully to the DB then force check/update values within config
    if dbErrorFlag:
        configFunctions.updateDatabaseConfig(configFile)
    else:
        logging.info(f"Successfully connected to database")

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

    # See if there are any sneaky people who should not be on the plex servers (and boot them if there are)
    checkPlexUsersNotInDatabase(configFile, dryrun=dryrun)

    # See if anyone with an inactive status is still somehow on the plex server
    checkInactiveUsersOnPlex(configFile, dryrun=dryrun)

    # Check for users with less than 7 days left or subscription has lapsed.
    checkUsersEndDate(configFile, dryrun=dryrun)

    # See if there are any sneaky people who should not have the discord role associated with plex access (and remove the role if they have it)
    checkInactiveUsersOnDiscord(configFile, dryrun=dryrun)

def main():
    parser = argparse.ArgumentParser(description='Harassarr Script')
    parser.add_argument('-add', metavar='service', help='Add a service (e.g., plex)')

    # Set default values based on environment variables
    default_dryrun = os.getenv('DRYRUN', 'false').lower() == 'true'
    default_time = os.getenv('TIME', '')

    parser.add_argument('--dryrun', action='store_true', default=default_dryrun, help='Run in dry-run mode')
    parser.add_argument('-time', metavar='time', type=str, default=default_time, help='Time that the script will run each day, use format HH:MM')

    args = parser.parse_args()
    dryrun = args.dryrun

    if args.time:
        try:
            # Attempt to parse the time string
            runTime = datetime.strptime(args.time, "%H:%M").time()
        except ValueError:
            print("Error: Invalid time format. Please use the format HH:MM.")
            exit(1)
    else:
        logging.info(f"No TIME to run set, running now once.")
        dailyRun(args, dryrun=dryrun)
        exit(0)

    # Log the starting message
    logging.info(f"Starting Daily Run at {runTime}")

    # Schedule the script to run at the specified time
    schedule.every().day.at(str(runTime)).do(dailyRun, args, dryrun=dryrun)

    # Run the scheduled jobs
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
