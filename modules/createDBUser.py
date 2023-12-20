# createDBUser.py

import re
import sys
import mysql.connector
import logging
import socket
import yaml

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE_PATH = './config/config.yml'

def validate_input(input_string, pattern):
    while not re.match(pattern, input_string):
        print("Invalid input. Please try again.")
        input_string = input()
    return input_string

def validate_server(server, port):
    try:
        # Try connecting to the server on the specified port
        with socket.create_connection((server, port), timeout=1):
            pass
        return True
    except (socket.timeout, socket.error):
        return False

def get_validated_input(prompt, pattern):
    user_input = input(prompt)
    user_input = validate_input(user_input, pattern)
    return user_input

def get_database_user_input():
    while True:
        server = get_validated_input("Enter IP address or hostname of database: ", r'^[a-zA-Z0-9.-]+$')
        port = 3306  # MariaDB default port

        if validate_server(server, port):
            break
        else:
            print("Could not connect to the database on port 3306. Please enter a valid IP address or hostname.")

    root_user = input("Enter root database user (default is root): ") or 'root'
    root_password = input("Enter root database password: ")
    new_user = input("Enter new username (default is lsql_harassarr): ") or 'lsql_harassarr'
    new_password = input("Enter new user password: ")
    database = input("Enter database name (default is media_mgmt): ") or 'media_mgmt'

    return root_user, root_password, new_user, new_password, database, server

def append_database_to_config(new_user, new_password, database, server, config_file_path):
    # Load existing config data
    with open(config_file_path, 'r') as config_file:
        config_data = yaml.safe_load(config_file)

    # Check if 'database' key exists
    if 'database' not in config_data:
        config_data['database'] = {}

    # Update or add database-related information
    config_data['database'].update({
        'user': new_user,
        'password': new_password,
        'host': server,
        'table': database
    })

    # Write the updated configuration back to config.yml
    with open(config_file_path, 'w') as config_file:
        yaml.dump(config_data, config_file)

def create_database_user(root_user, root_password, new_user, new_password, database='media_mgmt', server='localhost'):
    try:
        # Connect to MySQL using the root user to create the new user
        cnx = mysql.connector.connect(user=root_user, password=root_password, host=server)
        cursor = cnx.cursor()

        # Create the new user with all privileges on the specified database
        cursor.execute(f"CREATE USER '{new_user}'@'%' IDENTIFIED BY '{new_password}';")
        cursor.execute(f"GRANT ALL PRIVILEGES ON {database}.* TO '{new_user}'@'%';")
        cursor.execute("FLUSH PRIVILEGES;")
        logging.info(f"User '{new_user}' created with all privileges on database '{database}'.")

        # Append database information to the config.yml file
        append_database_to_config(new_user, new_password, database, server, CONFIG_FILE_PATH)

        cnx.commit()
        return True  # Return success

    except mysql.connector.Error as err:
        logging.error(f"Error: {err}")
        return False  # Return failure

    finally:
        # Close the cursor and connection
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals():
            cnx.close()

if __name__ == "__main__":
    # Read command-line arguments
    root_user, root_password, new_user, new_password, database, server = get_database_user_input()

    # Call the function to create the user
    success = create_database_user(
        root_user=root_user,
        root_password=root_password,
        new_user=new_user,
        new_password=new_password,
        database=database,
        server=server
    )

    if success:
        logging.info("User creation succeeded.")
    else:
        logging.error("User creation failed.")
