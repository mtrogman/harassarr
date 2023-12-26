# harassarr.py
import logging
import sys
import os
import argparse
from modules import dbFunctions, configFunctions, plexFunctions, validateFunctions

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
configFile = "./config/config.yml"

# harassarr.py
def checkPlexUsersNotInDatabase(configFile):
    try:
        # Load database configuration
        db_config = configFunctions.getConfig(configFile)['database']

        # Load Plex configuration
        plex_config = configFunctions.getConfig(configFile)

        # Validate database connection
        if not validateFunctions.validateDBConnection(**db_config):
            logging.error("Database connection failed. Please check your database configuration.")
            return

        # Get the list of users from the database
        db_users = dbFunctions.getDBUsers(**db_config)

        # Get the list of Plex users
        plex_users = plexFunctions.listPlexUsers(**plex_config)

        # Check for Plex users not in the database
        for plex_user in plex_users:
            if plex_user["Username"] not in db_users:
                logging.warning(f"Plex user '{plex_user['Username']}' with email '{plex_user['Email']}' has access but is not in the database.")

    except Exception as e:
        logging.error(f"Error checking Plex users not in the database: {e}")




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
                logging.info(f"Connecting to Plex instance: {serverName}")
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

    checkPlexUsersNotInDatabase(configFile)

if __name__ == "__main__":
    main()
