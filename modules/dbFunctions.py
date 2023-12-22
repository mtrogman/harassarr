#dbFunctions.py
import sys
import mysql.connector
import logging


logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def createDBUser(root_user, root_password, new_user, new_password, database, server):
    try:
        # Connect to MySQL using the root user to check if the user already exists
        cnx = mysql.connector.connect(user=root_user, password=root_password, host=server)
        cursor = cnx.cursor()

        # Check if the user already exists
        cursor.execute(f"SELECT 1 FROM mysql.user WHERE user = '{new_user}' LIMIT 1;")
        user_exists = cursor.fetchone()

        if user_exists:
            # User already exists, reset the password and update permissions
            cursor.execute(f"SET PASSWORD FOR '{new_user}'@'%' = PASSWORD('{new_password}');")
            cursor.execute(f"GRANT ALL PRIVILEGES ON {database}.* TO '{new_user}'@'%';")
            cursor.execute("FLUSH PRIVILEGES;")
            logging.info(f"User '{new_user}' exists. Password reset and permissions updated.")

        else:
            # User doesn't exist, create the new user with all privileges on the specified database
            cursor.execute(f"CREATE USER '{new_user}'@'%' IDENTIFIED BY '{new_password}';")
            cursor.execute(f"GRANT ALL PRIVILEGES ON {database}.* TO '{new_user}'@'%';")
            cursor.execute("FLUSH PRIVILEGES;")
            logging.info(f"User '{new_user}' created with all privileges on database '{database}'.")

    except mysql.connector.Error as err:
        logging.error("Database user creation or update failed.")
        logging.error(f"Error: {err}")
        return False  # Return failure

    finally:
        # Close the cursor and connection
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals():
            cnx.close()
    return True  # Return success


def createDBStructure(root_user, root_password, database, server):
    try:
        # Connect to MySQL using the root user to create the new user
        cnx = mysql.connector.connect(user=root_user, password=root_password, host=server)
        cursor = cnx.cursor()

        # Create the database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database};")
        logging.info(f"Database '{database}' in place.")

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
        logging.error("Database and table creation failed.")
        logging.error(f"Error: {err}")
        return False  

    finally:
        # Close the cursor and connection
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals():
            cnx.close()
    return True
