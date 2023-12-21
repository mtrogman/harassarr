#configFunctions.py
import os
import yaml
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def getConfig(file):
    with open(file, 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config


def checkConfig(configFile):
    # Create config directory if it doesn't exist
    os.makedirs(os.path.dirname(configFile), exist_ok=True)

    # Check if config file exists, if not, create it with an empty dictionary
    if not os.path.isfile(configFile):
        with open(configFile, 'w') as file:
            yaml.dump({}, file)
        logging.info(f"{configFile} did not exist.  Creating...")
        return False

    config = getConfig(configFile)

    if 'database' not in config:
        logging.info("Database configuration not found in config.yml.")
        return False

    if not all(key in config['database'] for key in ['user', 'password', 'host', 'table']):
        logging.info("Invalid or incomplete database configuration in config.yml.")
        # INJECT DEFAULT PLACEHOLDERS FOR MISSING KEYS
        return False
    else:
        return True


def updateDBInfo(configFile, host, table, user, password):
    config = getConfig(configFile)
    
    # Update the database section with the provided values
    config['database']['host'] = host
    config['database']['table'] = table
    config['database']['user'] = user
    config['database']['password'] = password

    # Write the updated configuration back to config.yml
    with open(configFile, 'w') as configFile:
        yaml.dump(config, configFile)

    logging.info("Database configuration updated in config.yml.")
