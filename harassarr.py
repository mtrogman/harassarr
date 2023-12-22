# harassarr.py
import logging
import sys
import argparse
import modules.dbFunctions as dbFunctions
import modules.configFunctions as configFunctions
import modules.plexFunctions as plexFunctions
import modules.validateFuncations as validateFunctions

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
configFile = "./config/config.yml"

def main():
    parser = argparse.ArgumentParser(description='Harassarr Script')
    parser.add_argument('-add', metavar='service', help='Add a service (e.g., plex)')

    args = parser.parse_args()

    # Validate Configuration is good
    configCheck = configFunctions.checkConfig(configFile)
    if configCheck:
        logging.info(f"Database portion of configuration file (config.yml) looks good")
        config = configFunctions.getConfig(configFile)
        host = config['database']['host']
        port = config['database']['port']
        database = config['database']['database']
        user = config['database']['user']
        password = config['database']['password']
        table = "users"
    else:
        #This should never happen but let's plan for weird stuff to occur.
        logging.error(f"Configuration check has failed, please try again.")
        exit(1)

    # Validate Connection to Database is good
    dbErrorFlag = False
    serverValidation = validateFunctions.validateServer(host, port)
    if not serverValidation:
        logging.error(f"Server {host} is NOT listening on {port}")
        dbErrorFlag = True
    databaseValidation = validateFunctions.validateDBConnection(user, password, host)
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

    # Extract PLEX configurations
    plexConfigurations = [
        config[key] for key in config if key.startswith('PLEX-')
    ]

    # Check if there are any PLEX configurations
    if len(plexConfigurations) == 0:
        logging.info("No valid PLEX configurations found in the config file. Creating PLEX configuration.")
        while True:
            plexFunctions.createPlexConfig(configFile)
            response = validateFunctions.getValidatedInput("Would you like to configure another Plex server? (Yes or No): ", r'(?i)^(yes|no)$')
            if response.lower() == 'no':
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
            print(plexUserInfo)

if __name__ == "__main__":
    main()
