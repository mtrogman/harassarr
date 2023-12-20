import mysql.connector
import yaml
import sys
import logging


logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def confirm_database_and_table():
    # Load database configuration from YAML file
    with open('./config/config.yml', 'r') as yaml_file:
        config_data = yaml.safe_load(yaml_file)

    db_config = {
        'user': config_data['database']['user'],
        'password': config_data['database']['password'],
        'host': config_data['database']['host'],
        'database': 'media_mgmt',  # Specify the new database name here
    }

    try:
        # Connect to MySQL to create the database
        cnx = mysql.connector.connect(user=db_config['user'], password=db_config['password'], host=db_config['host'])
        cursor = cnx.cursor()

        # Check if the database exists
        cursor.execute(f"SHOW DATABASES LIKE '{db_config['database']}';")
        database_exists = cursor.fetchone()

        if not database_exists:
            # Create the database if it doesn't exist
            cursor.execute(f"CREATE DATABASE {db_config['database']};")
            logging.info(f"Database '{db_config['database']}' created.")
        else:
            logging.info(f"Database {db_config['database']} already exists.")

        # Switch to the new database
        cursor.execute(f"USE {db_config['database']};")

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
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            print("Error: Access denied.")
        else:
            print(f"Error: {err}")
    finally:
        # Close the cursor and connection
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals():
            cnx.close()
