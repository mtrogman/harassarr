#dbFunctions.py
import sys
import csv
import mysql.connector
import logging
from datetime import datetime
import modules.configFunctions as configFunctions


logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def createDBUser(rootUser, rootPassword, newUser, newPassword, database, server):
    try:
        # Connect to MySQL using the root user to check if the user already exists
        cnx = mysql.connector.connect(user=rootUser, password=rootPassword, host=server)
        cursor = cnx.cursor()

        # Check if the user already exists
        cursor.execute(f"SELECT 1 FROM mysql.user WHERE user = '{newUser}' LIMIT 1;")
        userExists = cursor.fetchone()

        if userExists:
            # User already exists, reset the password and update permissions
            cursor.execute(f"SET PASSWORD FOR '{newUser}'@'%' = PASSWORD('{newPassword}');")
            cursor.execute(f"GRANT ALL PRIVILEGES ON {database}.* TO '{newUser}'@'%';")
            cursor.execute("FLUSH PRIVILEGES;")
            logging.info(f"User '{newUser}' exists. Password reset and permissions updated.")

        else:
            # User doesn't exist, create the new user with all privileges on the specified database
            cursor.execute(f"CREATE USER '{newUser}'@'%' IDENTIFIED BY '{newPassword}';")
            cursor.execute(f"GRANT ALL PRIVILEGES ON {database}.* TO '{newUser}'@'%';")
            cursor.execute("FLUSH PRIVILEGES;")
            logging.info(f"User '{newUser}' created with all privileges on database '{database}'.")

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


def createDBStructure(rootUser, rootPassword, database, server):
    try:
        # Connect to MySQL using the root user to create the new user
        cnx = mysql.connector.connect(user=rootUser, password=rootPassword, host=server)
        cursor = cnx.cursor()

        # Create the database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database};")
        logging.info(f"Database '{database}' in place.")

        # Switch to the new database
        cursor.execute(f"USE {database};")

        # Check if the table exists
        cursor.execute("SHOW TABLES LIKE 'users';")
        tableExists = cursor.fetchone()

        if not tableExists:
            # Define your table creation SQL statement
            createTableQuery = """
                CREATE TABLE `users` (
                    `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    `primaryEmail` VARCHAR(100) NULL DEFAULT '',
                    `secondaryEmail` VARCHAR(100) NULL DEFAULT 'n/a',
                    `primaryDiscord` VARCHAR(100) NULL DEFAULT '',
                    `primaryDiscordId` VARCHAR(25) NULL DEFAULT '',
                    `secondaryDiscord` VARCHAR(100) NULL DEFAULT 'n/a',
                    `secondaryDiscordId` VARCHAR(25) NULL DEFAULT '',
                    `notifyDiscord` VARCHAR(10) NULL DEFAULT 'primary',
                    `notifyEmail` VARCHAR(10) NULL DEFAULT 'primary',
                    `status` VARCHAR(10) NULL DEFAULT '',
                    `server` VARCHAR(25) NULL DEFAULT '',
                    `4k` ENUM('Yes', 'No'),
                    `paymentMethod` VARCHAR(25) NULL DEFAULT '',
                    `paymentPerson` VARCHAR(25) NULL DEFAULT '',
                    `paidAmount` DECIMAL(10, 2) NULL DEFAULT NULL,
                    `joinDate` DATE DEFAULT CURRENT_DATE,
                    `startDate` DATE DEFAULT CURRENT_DATE,
                    `endDate` DATE NULL DEFAULT NULL
                ) COLLATE='utf8_bin';
            """

            # Execute the table creation query
            cursor.execute(createTableQuery)
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


def injectUsersFromCSV(user, password, server, database, csvFilePath):
    # Database connection parameters
    dbConfig = {
        'host': server,
        'user': user,
        'password': password,
        'database': database
    }

    try:
        # Open database connection
        connection = mysql.connector.connect(**dbConfig)
        cursor = connection.cursor()

        # Read data from CSV file with utf-8 encoding
        with open(csvFilePath, 'r', encoding='utf-8') as csvFile:
            csvReader = csv.DictReader(csvFile)
            for row in csvReader:
                # Convert date strings to datetime objects if they are not empty
                startDateStr = row.get('startDate', '')
                endDateStr = row.get('endDate', '')
                joinedDateStr = row.get('joinDate', '')

                startDate = datetime.strptime(startDateStr, '%m/%d/%Y').date() if startDateStr else None
                endDate = datetime.strptime(endDateStr, '%m/%d/%Y').date() if endDateStr else None
                joinDate = datetime.strptime(joinedDateStr, '%m/%d/%Y').date() if joinedDateStr else None

                # SQL query to insert data into the 'users' table
                insert_query = """
                    INSERT INTO users (primaryDiscord, secondaryDiscord, primaryEmail, secondaryEmail,
                                primaryDiscordId, secondaryDiscordId,
                                notifyDiscord, notifyEmail, status, server, 4k, paidAmount,
                                paymentMethod, paymentPerson, startDate, endDate, joinDate)
                    VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """


                # Data to be inserted
                data = (
                    row.get('primaryDiscord', ''), row.get('secondaryDiscord', ''),
                    row.get('primaryEmail', ''), row.get('secondaryEmail', ''),
                    row.get('primaryDiscordId', ''), row.get('secondaryDiscordId', ''),
                    row.get('notifyDiscord', ''), row.get('notifyEmail', ''),
                    row.get('status', ''), row.get('server', ''), row.get('4k', ''),
                    row.get('paidAmount'), row.get('paymentMethod', ''),
                    row.get('paymentPerson', ''), startDate, endDate, joinDate
                )

                # Execute the SQL query
                cursor.execute(insert_query, data)
                logging.info(f"User {row.get('primaryEmail', '')} imported successfully.")

        # Commit changes and close connection
        connection.commit()
        connection.close()

        print("Data inserted successfully.")
    except Exception as e:
        print(f"Error: {e}")


def countDBUsers(user, password, server, database):
    # Database connection parameters
    dbConfig = {
        'host': server,
        'user': user,
        'password': password,
        'database': database
    }

    try:
        # Open database connection
        connection = mysql.connector.connect(**dbConfig)
        cursor = connection.cursor()

        # SQL query to count rows in the 'users' table
        countQuery = "SELECT COUNT(*) FROM users"

        # Execute the SQL query
        cursor.execute(countQuery)

        # Fetch the result
        count = cursor.fetchone()[0]

        # Close connection
        connection.close()

        return count
    except Exception as e:
        print(f"Error: {e}")
        return None


def getDBUsers(user, password, server, database):
    try:
        cnx = mysql.connector.connect(user=user, password=password, host=server, database=database)
        cursor = cnx.cursor()

        # Example query to retrieve usernames from a 'users' table
        query = "SELECT primaryEmail FROM users;"
        cursor.execute(query)

        # Fetch all usernames
        dbUsers = [row[0] for row in cursor.fetchall()]

        # Close the cursor and connection
        cursor.close()
        cnx.close()

        return dbUsers

    except mysql.connector.Error as err:
        raise ValueError(f"Error retrieving users from the database: {err}")


def userExists(user, password, server, database, primaryEmail, serverName):
    try:
        # Connect to the database
        connection = mysql.connector.connect(
            host=server,
            user=user,
            password=password,
            database=database
        )

        # Create a cursor object
        cursor = connection.cursor()

        # Query to check if the user exists in the database for the specific server
        query = "SELECT * FROM users WHERE LOWER(primaryEmail) = %s AND LOWER(server) = %s"
        cursor.execute(query, (primaryEmail.lower(), serverName.lower()))

        # Fetch the result
        result = cursor.fetchone()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        # Return True if the user exists, False otherwise
        return result is not None

    except mysql.connector.Error as e:
        logging.error(f"Error checking if user exists in the database: {e}")
        return False


def getUsersByStatus(user, password, host, database, status, serverName):
    try:
        # Connect to the database
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )

        # Create a cursor object
        cursor = connection.cursor(dictionary=True)  # Use dictionary cursor to fetch results as dictionaries

        # Query to select users by status and server name
        query = "SELECT * FROM users WHERE status = %s AND server = %s"
        cursor.execute(query, (status, serverName))

        # Fetch all users
        users = cursor.fetchall()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        return users

    except mysql.connector.Error as e:
        logging.error(f"Error getting users by status: {e}")
        return []


def updateUserStatus(configFile, serverName, userEmail, newStatus):
    config = configFunctions.getConfig(configFile)
    dbConfig = config.get('database', None)

    try:
        # Connect to the database
        connection = mysql.connector.connect(
            host=dbConfig['host'],
            user=dbConfig['user'],
            password=dbConfig['password'],
            database=dbConfig['database']
        )

        # Create a cursor object
        cursor = connection.cursor()

        # Validate the new_status input
        if newStatus not in ('Active', 'Inactive'):
            raise ValueError("Invalid status. Please provide 'Active' or 'Inactive'.")

        # Update the user status
        update_query = "UPDATE users SET status = %s WHERE primaryEmail = %s AND server = %s"
        cursor.execute(update_query, (newStatus, userEmail, serverName))

        # Commit the changes
        connection.commit()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        logging.info(f"User '{userEmail}' status updated to '{newStatus}' for server '{serverName}'.")

    except mysql.connector.Error as e:
        logging.error(f"Error updating user status: {e}")


def getDBField(configFile, serverName, userEmail, field):
    try:
        # Load database configuration
        dbConfig = configFunctions.getConfig(configFile)['database']

        # Connect to the database
        connection = mysql.connector.connect(
            host=dbConfig['host'],
            user=dbConfig['user'],
            password=dbConfig['password'],
            database=dbConfig['database']
        )

        # Create a cursor object
        cursor = connection.cursor(dictionary=True)  # Use dictionary cursor to fetch results as dictionaries

        # Query to select the specified field for the given user
        query = f"SELECT {field} FROM users WHERE server = %s AND primaryEmail = %s"
        cursor.execute(query, (serverName, userEmail))

        # Fetch the field value
        result = cursor.fetchone()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        return result[field] if result else None

    except mysql.connector.Error as e:
        logging.error(f"Error getting {field} value: {e}")
        return None
    

def getAllFieldsForUser(configFile, serverName, userEmail):
    try:
        # Load database configuration
        dbConfig = configFunctions.getConfig(configFile)['database']

        # Connect to the database
        connection = mysql.connector.connect(
            host=dbConfig['host'],
            user=dbConfig['user'],
            password=dbConfig['password'],
            database=dbConfig['database']
        )

        # Create a cursor object
        cursor = connection.cursor(dictionary=True)  # Use dictionary cursor to fetch results as dictionaries

        # Query to select all fields for the given user
        query = "SELECT * FROM users WHERE server = %s AND primaryEmail = %s"
        cursor.execute(query, (serverName, userEmail))

        # Fetch the result
        result = cursor.fetchone()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        return result if result else None

    except mysql.connector.Error as e:
        logging.error(f"Error getting all fields for the user: {e}")
        return None
