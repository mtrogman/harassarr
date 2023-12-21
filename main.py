# main.py
import logging
import sys
import modules.dbFunctions as dbFunctions
import modules.configFunctions as configFunctions

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
configFile = "./config/config.yml"

def main():
    check = configFunctions.checkConfig(configFile)
    # fix config
    if check is False:
        # reprompt for host, table, user, password.  Set the default of these values as what existed in the config (if nothing existed in config utilize the normal default)
        config = configFunctions.getConfig(configFile)
        if 'database' not in config:
            logging.info("Database configuration not found in config.yml. Using default configuration.")
            # Create a default structure for the config file
            default_config = {
                'database': {
                    'host': '',
                    'table': 'media_mgmt',
                    'user': 'lsql_harassarr',
                    'password': '',
                }
            }
            # Update the existing config with default values
            config.update(default_config)
            with open(configFile, 'w') as file:
                yaml.dump(config, file)
        
        # Set default values based on existing config or use normal defaults
        host = config['database'].get('host', 'default_host')
        table = config['database'].get('table', 'default_table')
        user = config['database'].get('user', 'default_user')
        password = config['database'].get('password', 'default_password')
        # validate inputs are successful
        host, table, user, password = dbFunctions.updateDatabaseConfig(host, table, user, password)
        # update config.yml's database (host, table, user, password) with the input from above
        configFunctions.updateDBInfo(host, table, user, password)
        # Validate the connection with the updated values
        dbFunctions.validate_connection(user, password, host)
    else:
        config = configFunctions.getConfig(configFile)
        dbFunctions.validate_connection(config['database']['user'], config['database']['password'], config['database']['host'])
        # update config.yml's database (host, table, user, password) if values changed


if __name__ == "__main__":
    main()
