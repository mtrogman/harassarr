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
        logging.info(f"Configuration file (config.yml) looks good")
    config = configFunctions.getConfig(configFile)
    host = config['database']['host']
    port = config['database']['port']
    database = config['database']['database']
    user = config['database']['user']
    password = config['database']['password']
    table = "users"

    # Validate Connection to Database is good
    serverValidation = validateFunctions.validateServer(host, port)
    if serverValidation:
        logging.info(f"Server {host} is listening on {port}")
    databaseValidation = validateFunctions.validateDBConnection(user, password, host)
    if databaseValidation:
        logging.info(f"Authenticated with {user} to {host} sucessfully")
    validateDBDatabase = validateFunctions.validateDBDatabase(user, password, host, database)
    if validateDBDatabase:
        logging.info(f"Database {database} exists on {host}")
    tableValidation = validateFunctions.validateDBTable(user, password, host, database, table)
    if tableValidation:
        logging.info(f"Table {table} exists on {database}")

    # Validate Connection to Plex is good
    plexValidation = plexFunctions.createPlexConfig(configFile)


if __name__ == "__main__":
    main()
