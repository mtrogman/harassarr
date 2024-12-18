import logging, mysql.connector, sys
from datetime import datetime
import modules.configFunctions as configFunctions

# Configure logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DBFunctions")


# Helper Functions
def connect_to_database(db_config):
    """
    Establish a connection to the database.

    Args:
        db_config (dict): Database configuration dictionary.

    Returns:
        mysql.connector.connection.MySQLConnection: Database connection object.
    """
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except mysql.connector.Error as err:
        logger.error(f"Failed to connect to the database: {err}")
        return None


def execute_query(query, params=None, fetch_one=False, fetch_all=False, db_config=None):
    """
    Execute a database query with optional parameters.

    Args:
        query (str): SQL query string.
        params (tuple): Parameters for the query.
        fetch_one (bool): Fetch a single result.
        fetch_all (bool): Fetch all results.
        db_config (dict): Database configuration dictionary.

    Returns:
        Any: Query result or None if the query fails.
    """
    if not db_config:
        logger.error("Database configuration is missing.")
        return None

    connection = connect_to_database(db_config)
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True if fetch_one or fetch_all else False)
        cursor.execute(query, params)
        result = None
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        connection.commit()
        return result
    except mysql.connector.Error as err:
        logger.error(f"Error executing query: {err}")
        return None
    finally:
        cursor.close()
        connection.close()


# Main Functions
def count_db_users(db_config):
    """
    Count the number of users in the 'users' table.

    Args:
        db_config (dict): Database configuration dictionary.

    Returns:
        int: Number of users or None if the query fails.
    """
    query = "SELECT COUNT(*) AS user_count FROM users"
    result = execute_query(query, db_config=db_config, fetch_one=True)
    return result["user_count"] if result else None


def get_db_users(db_config):
    """
    Retrieve a list of primary emails from the 'users' table.

    Args:
        db_config (dict): Database configuration dictionary.

    Returns:
        list: List of primary emails or an empty list if the query fails.
    """
    query = "SELECT primaryEmail FROM users"
    result = execute_query(query, db_config=db_config, fetch_all=True)
    return [row["primaryEmail"] for row in result] if result else []


def user_exists(db_config, primary_email, server_name):
    """
    Check if a user exists in the 'users' table for a specific server.

    Args:
        db_config (dict): Database configuration dictionary.
        primary_email (str): Primary email of the user.
        server_name (str): Server name.

    Returns:
        bool: True if the user exists, False otherwise.
    """
    if not primary_email or not server_name:
        logger.error("Invalid input: primary_email and server_name are required.")
        return False

    query = "SELECT 1 FROM users WHERE LOWER(primaryEmail) = %s AND LOWER(server) = %s"
    result = execute_query(query, params=(primary_email.lower(), server_name.lower()), db_config=db_config, fetch_one=True)
    return bool(result)


def get_users_by_status(db_config, status, server_name="*"):
    """
    Retrieve users by their status and server name.

    Args:
        db_config (dict): Database configuration dictionary.
        status (str): User status ('Active', 'Inactive').
        server_name (str): Server name. Use '*' to retrieve users across all servers.

    Returns:
        list: List of users matching the criteria or an empty list if the query fails.
    """
    if server_name == "*":
        query = "SELECT * FROM users WHERE status = %s"
        params = (status,)
    else:
        query = "SELECT * FROM users WHERE status = %s AND server = %s"
        params = (status, server_name)

    result = execute_query(query, params=params, db_config=db_config, fetch_all=True)
    return result if result else []


def update_user_status(db_config, server_name, primary_email, new_status):
    """
    Update the status of a user in the 'users' table.

    Args:
        db_config (dict): Database configuration dictionary.
        server_name (str): Server name.
        primary_email (str): Primary email of the user.
        new_status (str): New status ('Active', 'Inactive').

    Returns:
        bool: True if the update is successful, False otherwise.
    """
    if new_status not in ("Active", "Inactive"):
        logger.error("Invalid status. Please use 'Active' or 'Inactive'.")
        return False

    query = "UPDATE users SET status = %s WHERE primaryEmail = %s AND server = %s"
    result = execute_query(query, params=(new_status, primary_email, server_name), db_config=db_config)
    if result is not None:
        logger.info(f"User {primary_email} status updated to {new_status} on server {server_name}.")
        return True
    return False


def get_user_field(db_config, server_name, primary_email, field):
    """
    Retrieve a specific field for a user.

    Args:
        db_config (dict): Database configuration dictionary.
        server_name (str): Server name.
        primary_email (str): Primary email of the user.
        field (str): Field name to retrieve.

    Returns:
        Any: Field value or None if the query fails.
    """
    query = f"SELECT {field} FROM users WHERE server = %s AND primaryEmail = %s"
    result = execute_query(query, params=(server_name, primary_email), db_config=db_config, fetch_one=True)
    return result[field] if result else None


def get_all_fields_for_user(db_config, server_name, primary_email):
    """
    Retrieve all fields for a specific user.

    Args:
        db_config (dict): Database configuration dictionary.
        server_name (str): Server name.
        primary_email (str): Primary email of the user.

    Returns:
        dict: User record as a dictionary or None if the query fails.
    """
    query = "SELECT * FROM users WHERE server = %s AND primaryEmail = %s"
    result = execute_query(query, params=(server_name, primary_email), db_config=db_config, fetch_one=True)
    return result if result else None
