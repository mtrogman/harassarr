import sys, logging, socket, re, mysql.connector
from plexapi.server import PlexServer


# Logging configuration
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("ValidateFunctions")


def validate_server(server, port):
    """
    Validates if a server is reachable on a specific port.
    
    Args:
        server (str): The server address.
        port (int): The port number.

    Returns:
        bool: True if the server is reachable, False otherwise.
    """
    logger.debug(f"Validating server {server} on port {port}.")
    try:
        with socket.create_connection((server, port), timeout=1):
            logger.info(f"Server {server} is reachable on port {port}.")
            return True
    except (socket.timeout, socket.error) as e:
        logger.error(f"Server {server} is NOT reachable on port {port}: {e}")
        return False


def validate_db_connection(user, password, server, database):
    """
    Validates the connection to a specific database.

    Args:
        user (str): The database user.
        password (str): The user's password.
        server (str): The database server address.
        database (str): The database name.

    Returns:
        bool: True if the connection is successful, False otherwise.
    """
    logger.debug(f"Validating database connection to {server}/{database}.")
    try:
        with mysql.connector.connect(user=user, password=password, host=server, database=database):
            logger.info(f"Successfully connected to database {database} on {server}.")
            return True
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {err}")
        return False


def validate_db_exists(user, password, server, database):
    """
    Checks if a specific database exists.

    Args:
        user (str): The database user.
        password (str): The user's password.
        server (str): The database server address.
        database (str): The database name to check.

    Returns:
        bool: True if the database exists, False otherwise.
    """
    logger.debug(f"Checking if database {database} exists on {server}.")
    try:
        with mysql.connector.connect(user=user, password=password, host=server) as cnx:
            cursor = cnx.cursor()
            cursor.execute(f"SHOW DATABASES LIKE '{database}';")
            result = cursor.fetchone()
            cursor.close()
            if result:
                logger.info(f"Database {database} exists on {server}.")
            else:
                logger.warning(f"Database {database} does NOT exist on {server}.")
            return bool(result)
    except mysql.connector.Error as err:
        logger.error(f"Error while checking database existence: {err}")
        return False


def validate_table_exists(user, password, server, database, table):
    """
    Checks if a specific table exists in a database.

    Args:
        user (str): The database user.
        password (str): The user's password.
        server (str): The database server address.
        database (str): The database name.
        table (str): The table name to check.

    Returns:
        bool: True if the table exists, False otherwise.
    """
    logger.debug(f"Checking if table {table} exists in database {database}.")
    try:
        with mysql.connector.connect(user=user, password=password, host=server, database=database) as cnx:
            cursor = cnx.cursor()
            cursor.execute(f"SHOW TABLES LIKE '{table}';")
            result = cursor.fetchone()
            cursor.close()
            if result:
                logger.info(f"Table {table} exists in database {database}.")
            else:
                logger.warning(f"Table {table} does NOT exist in database {database}.")
            return bool(result)
    except mysql.connector.Error as err:
        logger.error(f"Error while checking table existence: {err}")
        return False


def get_validated_input(prompt, pattern):
    """
    Prompts the user for input and validates it against a regex pattern.

    Args:
        prompt (str): The input prompt message.
        pattern (str): The regex pattern to validate the input.

    Returns:
        str: The validated input string.
    """
    logger.debug(f"Prompting user with: {prompt}")
    while True:
        user_input = input(prompt)
        if re.match(pattern, user_input):
            logger.debug(f"Valid input received: {user_input}")
            return user_input
        logger.warning("Invalid input. Please try again.")


def validate_plex(base_url, token):
    """
    Validates if the Plex server is accessible with the provided base URL and token.

    Args:
        base_url (str): The Plex server's base URL.
        token (str): The Plex server's authentication token.

    Returns:
        bool: True if the Plex server is accessible, False otherwise.
    """
    logger.debug(f"Validating Plex server at {base_url}.")
    try:
        plex = PlexServer(base_url, token)
        logger.info(f"Successfully authenticated with Plex server at {base_url}.")
        return True
    except Exception as e:
        logger.error("Failed to authenticate with Plex server.")
        logger.error(
            "This may be due to Plex API rate limiting if the bot was restarted multiple times recently."
        )
        logger.error(f"Error: {e}")
        return False
