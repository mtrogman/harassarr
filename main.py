import os
import yaml
import logging
import sys

from modules.createDBUser import create_database_user, get_database_user_input
from modules.confirmDB import confirm_database_and_table

CONFIG_FILE = './config/config.yml'
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_config():
    # Create config directory if it doesn't exist
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    # Check if config file exists, if not, create it with an empty dictionary
    if not os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as config_file:
            yaml.dump({}, config_file)

def main():
    check_config()

    # Load configuration
    with open(CONFIG_FILE, 'r') as yaml_file:
        config_data = yaml.safe_load(yaml_file)

    if 'database' not in config_data:
        logging.info("Database configuration not found in config.yml.")
        # Run createDBUser.py to create the database and user
        root_user, root_password, new_user, new_password, database, server = get_database_user_input()
        create_database_user(root_user, root_password, new_user, new_password, database, server)

    confirm_database_and_table()

if __name__ == "__main__":
    main()
