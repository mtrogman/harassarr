#dbFunctions.py
import re
import sys
import mysql.connector
import logging
import socket
import yaml
import os

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

port = 3306  # MariaDB default port


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


def updateDatabaseConfig(host, table, user, password):
    host = input(f"Enter host (default is {host}): ") or host
    table = input(f"Enter table (default is {table}): ") or table
    user = input(f"Enter user (default is {user}): ") or user
    password = input("Enter new password (or to keep same password leave blank and hit enter): ") or password
    cnx = mysql.connector.connect(user=user, password=password, host=server)
    if cnx:
        cnx.close()
    else:
        if not validate_server(server, port):
            while True:
                logging.error(f"Could not connect to the database on port 3306. Please enter a valid IP address or hostname.")
                server = get_validated_input("Enter IP address or hostname of database: ", r'^[a-zA-Z0-9.-]+$')

                if validate_server(server, port):
                    break
        else:
            while True:
                logging.error(f"Could not connect to the database with the credentials provided.  Please enter valid creds.")
                user = input("Enter new username (default is lsql_harassarr): ") or 'lsql_harassarr'
                password = input("Enter new user password: ")
                cnx = mysql.connector.connect(user=user, password=password, host=server)
                if cnx:
                    cnx.close()
                    break
                else:
                    logging.error(f"Could not connect to the database with the credentials provided.  Please enter valid creds.")
    return host, table, user, password

def validate_connection(user, password, server):
    cnx = mysql.connector.connect(user=user, password=password, host=server)
    if cnx:
        cnx.close()
    else:
        logging.error(f"Could not connect to the database with information in config.yml")
        if not validate_server(server, port):
            logging.error(f"Could not connect to the database on port 3306. Please enter a valid IP address or hostname.")
            while True:
                server = get_validated_input("Enter IP address or hostname of database: ", r'^[a-zA-Z0-9.-]+$')

                if validate_server(server, port):
                    break
                else:
                    logging.error(f"Could not connect to the database on port 3306. Please enter a valid IP address or hostname.")
        else:
            logging.error(f"Could not connect to the database with the credentials provided.  Please enter valid creds.")
            while True:
                user = input("Enter new username (default is lsql_harassarr): ") or 'lsql_harassarr'
                password = input("Enter new user password: ")
                # Connect to MySQL using the root user to create the new user
                cnx = mysql.connector.connect(user=user, password=password, host=server)
                if cnx:
                    cnx.close()
                    break
                else:
                    print("Could not connect to the database with the credentials provided.  Please enter valid creds.")



def get_validated_input(prompt, pattern):
    user_input = input(prompt)
    user_input = validate_input(user_input, pattern)
    return user_input


def get_database_user_input():
    while True:
        server = get_validated_input("Enter IP address or hostname of database: ", r'^[a-zA-Z0-9.-]+$')

        if validate_server(server, port):
            break
        else:
            print("Could not connect to the database on port 3306. Please enter a valid IP address or hostname.")

    while True:
        root_user = input("Enter root database user (default is root): ") or 'root'
        root_password = input("Enter root database password: ")
        # Connect to MySQL using the root user to create the new user
        cnx = mysql.connector.connect(user=root_user, password=root_password, host=server)
        if cnx:
            cnx.close()
            break
        else:
            print("Could not connect to the database with the credentials provided.  Please enter valid creds.")

    new_user = input("Enter new username (default is lsql_harassarr): ") or 'lsql_harassarr'
    new_password = input("Enter new user password: ")
    database = input("Enter database name (default is media_mgmt): ") or 'media_mgmt'

    return root_user, root_password, new_user, new_password, database, server


def create_database_and_table(root_user, root_password, new_user, new_password, database, server):
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
        append_database_to_config(new_user, new_password, database, server, CONFIG_FILE)

        # Create the database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database};")
        logging.info(f"Database '{database}' created.")

        # Switch to the new database
        cursor.execute(f"USE {database};")

        # Check if the table exists
        cursor.execute("SHOW TABLES LIKE 'users';")
        table_exists = cursor.fetchone()

        if not table_exists:
            # Define your table creation SQL statement
            create_table_query = """
            CREATE TABLE `users` (
                `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                `primaryEmail` VARCHAR(100) NULL DEFAULT '',
                `secondaryEmail` VARCHAR(100) NULL DEFAULT 'n/a',
                `primaryDiscord` VARCHAR(100) NULL DEFAULT '',
                `secondaryDiscord` VARCHAR(100) NULL DEFAULT 'n/a',
                `notifyDiscord` VARCHAR(10) NULL DEFAULT 'primary',
                `notifyEmail` VARCHAR(10) NULL DEFAULT 'primary',
                `status` VARCHAR(10) NULL DEFAULT '',
                `server` VARCHAR(25) NULL DEFAULT '',
                `4k` VARCHAR(25) NULL DEFAULT '',
                `paymentMethod` VARCHAR(25) NULL DEFAULT '',
                `paymentPerson` VARCHAR(25) NULL DEFAULT '',
                `joinDate` DATE DEFAULT CURRENT_DATE,
                `endDate` DATE NULL DEFAULT NULL
            ) COLLATE='utf8_bin';
            """

            # Execute the table creation query
            cursor.execute(create_table_query)
            logging.info("Table 'users' created.")
        else:
            logging.info("Table 'users' already exists.")

        cnx.commit()

    except mysql.connector.Error as err:
        logging.error(f"Error: {err}")
        return False  # Return failure

    finally:
        # Close the cursor and connection
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals():
            cnx.close()
    return True  # Return success


if __name__ == "__main__":
    # Read command-line arguments
    root_user, root_password, new_user, new_password, database, server = get_database_user_input()

    # Call the function to create the user, database, and table
    success = create_database_and_table(
        root_user=root_user,
        root_password=root_password,
        new_user=new_user,
        new_password=new_password,
        database=database,
        server=server
    )

    if success:
        logging.info("User, database, and table creation succeeded.")
    else:
        logging.error("User, database, and table creation failed.")
