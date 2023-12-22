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

    # Validate Connection to Plex is good

    # plexCreation = plexFunctions.createPlexConfig(configFile)



if __name__ == "__main__":
    main()
