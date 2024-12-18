import os, yaml, logging, sys, mysql.connector
from modules import dbFunctions, validateFunctions

# Configure logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ConfigFunctions")


# Helper Functions
def load_config(file_path):
    """
    Load YAML configuration file.

    Args:
        file_path (str): Path to the YAML file.

    Returns:
        dict: Configuration data.
    """
    try:
        with open(file_path, "r") as yaml_file:
            config = yaml.safe_load(yaml_file) or {}
        logger.debug(f"Configuration loaded from {file_path}.")
        return config
    except yaml.YAMLError as e:
        logger.error(f"Error loading YAML from {file_path}: {e}")
        return {}


def save_config(file_path, config):
    """
    Save configuration data to a YAML file.

    Args:
        file_path (str): Path to the YAML file.
        config (dict): Configuration data to save.
    """
    try:
        with open(file_path, "w") as yaml_file:
            yaml.dump(config, yaml_file, default_flow_style=False)
        logger.info(f"Configuration saved to {file_path}.")
    except IOError as e:
        logger.error(f"Error saving configuration to {file_path}: {e}")


def ensure_config_file_exists(file_path):
    """
    Ensure the configuration file exists; create an empty file if missing.

    Args:
        file_path (str): Path to the configuration file.
    """
    if not os.path.isfile(file_path):
        with open(file_path, "w") as file:
            yaml.dump({}, file)
        logger.info(f"{file_path} did not exist. An empty configuration file has been created.")


# Main Functions
def check_config(config_file):
    """
    Check and validate the configuration file.

    Args:
        config_file (str): Path to the configuration file.
    """
    ensure_config_file_exists(config_file)
    config = load_config(config_file)

    if "database" not in config:
        logger.info("Database configuration not found in config.yml.")
        create_database_config(config_file)

    required_keys = ["user", "password", "host", "database", "port"]
    if not all(key in config.get("database", {}) for key in required_keys):
        logger.warning("Incomplete or invalid database configuration in config.yml.")
        update_database_config(config_file)


def create_database_config(config_file):
    """
    Create a new database configuration.

    Args:
        config_file (str): Path to the configuration file.
    """
    logger.info("Creating new database configuration.")

    # Get database connection details
    server = validateFunctions.getValidatedInput(
        "Enter IP address or hostname of database: ", r"^[a-zA-Z0-9.-]+$"
    )
    port = int(validateFunctions.getValidatedInput(
        "Enter port utilized by the database (default is 3306): ", r"^[0-9]+$"
    ) or "3306")

    while not validateFunctions.validateServer(server, port):
        logger.error(f"Could not connect to the database on port {port}. Please enter valid details.")
        server = validateFunctions.getValidatedInput(
            "Enter IP address or hostname of database: ", r"^[a-zA-Z0-9.-]+$"
        )
        port = int(validateFunctions.getValidatedInput(
            "Enter port utilized by the database (default is 3306): ", r"^[0-9]+$"
        ) or "3306")

    # Get root credentials for database
    root_user = input("Enter root database user (default is root): ") or "root"
    root_password = input("Enter root database password: ")

    while not validate_db_credentials(root_user, root_password, server):
        logger.error("Invalid root credentials. Please try again.")
        root_user = input("Enter root database user (default is root): ") or "root"
        root_password = input("Enter root database password: ")

    # Get new user and database details
    new_user = input("Enter new username (default is lsql_harassarr): ") or "lsql_harassarr"
    new_password = input("Enter new user password: ")
    database = input("Enter database name (default is media_mgmt): ") or "media_mgmt"

    # Create database structure and user
    if dbFunctions.createDBStructure(root_user, root_password, database, server):
        if dbFunctions.createDBUser(root_user, root_password, new_user, new_password, database, server):
            config = load_config(config_file)
            config["database"] = {
                "user": new_user,
                "password": new_password,
                "host": server,
                "port": port,
                "database": database,
            }
            save_config(config_file, config)
            logger.info("Database configuration created successfully.")


def validate_db_credentials(user, password, server):
    """
    Validate database credentials.

    Args:
        user (str): Database username.
        password (str): Database password.
        server (str): Database server.

    Returns:
        bool: True if credentials are valid, False otherwise.
    """
    logger.debug(f"Validating credentials for user {user} on server {server}.")
    try:
        with mysql.connector.connect(user=user, password=password, host=server) as cnx:
            return True
    except mysql.connector.Error as e:
        logger.error(f"Failed to validate database credentials: {e}")
        return False


def update_database_config(config_file):
    """
    Update the existing database configuration.

    Args:
        config_file (str): Path to the configuration file.
    """
    logger.info("Updating database configuration.")
    config = load_config(config_file)
    db_config = config.get("database", {})

    # Update server details
    server = validateFunctions.getValidatedInput(
        f"Confirm database host (Current: {db_config.get('host', '')}): ", r"^[a-zA-Z0-9.-]+$"
    ) or db_config.get("host", "")
    port = int(validateFunctions.getValidatedInput(
        f"Confirm database port (Current: {db_config.get('port', 3306)}): ", r"^[0-9]+$"
    ) or db_config.get("port", 3306))

    # Validate server connection
    while not validateFunctions.validateServer(server, port):
        logger.error(f"Could not connect to the database on port {port}. Please enter valid details.")
        server = validateFunctions.getValidatedInput(
            "Enter IP address or hostname of database: ", r"^[a-zA-Z0-9.-]+$"
        )
        port = int(validateFunctions.getValidatedInput(
            "Enter port utilized by the database (default is 3306): ", r"^[0-9]+$"
        ) or "3306")

    # Update user and database details
    user = input(f"Enter new username (current: {db_config.get('user', '')}): ") or db_config.get("user", "")
    password = input(f"Enter new password: ") or db_config.get("password", "")
    database = validateFunctions.getValidatedInput(
        f"Enter new database name (current: {db_config.get('database', '')}): ", r"^[a-zA-Z0-9._-]+$"
    ) or db_config.get("database", "")

    if validate_db_credentials(user, password, server):
        config["database"] = {
            "user": user,
            "password": password,
            "host": server,
            "port": port,
            "database": database,
        }
        save_config(config_file, config)
        logger.info("Database configuration updated successfully.")
    else:
        logger.error("Failed to update database configuration. Invalid credentials.")
