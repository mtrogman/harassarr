# main.py
import logging
import sys
import modules.dbFunctions as dbFunctions
import modules.configFunctions as configFunctions

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
configFile = "./config/config.yml"

def main():
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
    serverValidation = configFunctions.validateServer(host, port)
    if serverValidation:
        logging.info(f"Server {host} is listening on {port}")
    databaseValidation = configFunctions.validateDBConnection(user, password, host)
    if databaseValidation:
        logging.info(f"Authenticated with {user} to {host} sucessfully")
    validateDBDatabase = configFunctions.validateDBDatabase(user, password, host, database)
    if validateDBDatabase:
        logging.info(f"Database {database} exists on {host}")
    tableValidation = configFunctions.validateDBTable(user, password, host, database, table)
    if tableValidation:
        logging.info(f"Table {table} exists on {database}")


if __name__ == "__main__":
    main()
