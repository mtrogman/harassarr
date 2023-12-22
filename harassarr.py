# main.py
import logging
import sys
import modules.dbFunctions as dbFunctions
import modules.configFunctions as configFunctions
import modules.plexFunctions as plexFunctions
import modules.validateFuncations as validateFunctions

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
configFile = "./config/config.yml"

def main():
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
    db_error_flag = False
    serverValidation = validateFunctions.validateServer(host, port)
    if not serverValidation:
        logging.error(f"Server {host} is NOT listening on {port}")
        db_error_flag = True
    databaseValidation = validateFunctions.validateDBConnection(user, password, host)
    if not databaseValidation:
        logging.error(f"Unable to authenticated with {user} to {host}")
        db_error_flag = True
    validateDBDatabase = validateFunctions.validateDBDatabase(user, password, host, database)
    if not validateDBDatabase:
        logging.error(f"Database {database} does not exists on {host}")
        db_error_flag = True
    tableValidation = validateFunctions.validateDBTable(user, password, host, database, table)
    if not tableValidation:
        logging.error(f"Table {table} does not exists on {database}")
        db_error_flag = True

    # If unable to connect fully to the DB then force check/update values within config
    if db_error_flag:
        configFunctions.updateDatabaseConfig(configFile)

    # Extract PLEX configurations
    plex_configurations = [
        config[key] for key in config if key.startswith('PLEX-')
    ]

    # Check if there are any PLEX configurations
    if len(plex_configurations) == 0:
        logging.info("No valid PLEX configurations found in the config file. Creating PLEX configuration.")
        while True:
            plexFunctions.createPlexConfig(configFile)
            response = validateFunctions.getValidatedInput("Would you like to configure another Plex server? (Yes or No): ", r'(?i)^(yes|no)$')
            if response.lower() == 'no':
                break


    else:
        logging.info("PLEX configuration(s) found in the config file (config.yml).")

        for config in plex_configurations:
            base_url = config.get("base_url")
            token = config.get("token")
            server_name = config.get("server_name")

            if base_url and token:
                logging.info(f"Connecting to Plex instance: {server_name}")
                plexValidation = validateFunctions.validatePlex(base_url, token)
                if plexValidation:
                    logging.info(f"Successfully connected to Plex instance: {server_name}")
            else:
                logging.warning(f"Skipping invalid PLEX configuration entry: {config}")




if __name__ == "__main__":
    main()
