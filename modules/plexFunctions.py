import sys, logging, yaml
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
import modules.configFunctions as configFunctions
import modules.emailFunctions as emailFunctions
import modules.discordFunctions as discordFunctions
import modules.dbFunctions as dbFunctions

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper Functions
def get_plex_config(config, server_name):
    """
    Retrieve the Plex configuration for a given server name.

    Args:
        config (dict): The global configuration dictionary.
        server_name (str): The name of the Plex server.

    Returns:
        dict: The Plex server configuration, or None if not found.
    """
    return config.get(f'PLEX-{server_name}', None)


def authenticate_plex(base_url, token):
    """
    Authenticate to the Plex server using the given credentials.

    Args:
        base_url (str): The base URL of the Plex server.
        token (str): The Plex authentication token.

    Returns:
        PlexServer: The authenticated Plex server instance.
    """
    try:
        return PlexServer(base_url, token)
    except Exception as e:
        logging.error(f"Error authenticating to Plex server: {e}")
        return None


# Main Functions
def list_plex_users(base_url, token, server_name, standard_libraries, optional_libraries):
    """
    List all users on a Plex server.

    Args:
        base_url (str): The base URL of the Plex server.
        token (str): The Plex authentication token.
        server_name (str): The name of the Plex server.
        standard_libraries (list): List of standard library names.
        optional_libraries (list): List of optional (e.g., 4K) library names.

    Returns:
        list: A list of user dictionaries.
    """
    plex = authenticate_plex(base_url, token)
    if not plex:
        return []

    users = plex.myPlexAccount().users()
    user_list = []

    for user in users:
        for server_info in user.servers:
            if server_name == server_info.name:
                num_libraries = server_info.numLibraries
                has_optional = num_libraries >= len(standard_libraries) + len(optional_libraries)
                fourk = "Yes" if has_optional else "No"

                if num_libraries < len(standard_libraries):
                    logging.warning(f"{user.email} ({user.title}) has fewer libraries shared than expected.")
                elif num_libraries > len(standard_libraries) + len(optional_libraries):
                    logging.warning(f"{user.email} ({user.title}) has extra libraries shared.")

                user_list.append({
                    "User ID": user.id,
                    "Username": user.title,
                    "Email": user.email,
                    "Server": server_name,
                    "Number of Libraries": num_libraries,
                    "All Libraries Shared": server_info.allLibraries,
                    "4K Libraries": fourk,
                })

    return user_list


def remove_plex_user(config_file, server_name, user_email, shared_libraries, dry_run):
    """
    Remove a user from a Plex server and notify them.

    Args:
        config_file (str): Path to the configuration file.
        server_name (str): The name of the Plex server.
        user_email (str): The email address of the user to remove.
        shared_libraries (list): List of shared library names.
        dry_run (bool): If True, perform a dry run without actual changes.

    Returns:
        None
    """
    config = configFunctions.getConfig(config_file)
    plex_config = get_plex_config(config, server_name)

    if not plex_config:
        logging.error(f"No configuration found for Plex server '{server_name}'.")
        return

    base_url = plex_config.get("baseUrl")
    token = plex_config.get("token")

    if not base_url or not token:
        logging.error(f"Invalid configuration for Plex server '{server_name}'.")
        return

    plex = authenticate_plex(base_url, token)
    if not plex:
        return

    if dry_run:
        logging.info(f"Dry run: Skipping removal of user '{user_email}' from server '{server_name}'.")
        return

    try:
        plex.myPlexAccount().updateFriend(user=user_email, sections=shared_libraries, server=plex, removeSections=True)
        logging.info(f"User '{user_email}' successfully removed from libraries on server '{server_name}'.")
    except Exception as e:
        logging.error(f"Error removing user '{user_email}' from Plex server '{server_name}': {e}")
        return

    notify_user_removal(config_file, server_name, user_email, dry_run)


def notify_user_removal(config_file, server_name, user_email, dry_run):
    """
    Notify a user via email and Discord about their subscription removal.

    Args:
        config_file (str): Path to the configuration file.
        server_name (str): The name of the Plex server.
        user_email (str): The email address of the user to notify.
        dry_run (bool): If True, log the action without sending notifications.

    Returns:
        None
    """
    try:
        # Email notification
        notify_email = dbFunctions.getDBField(config_file, server_name, user_email, "notifyEmail")
        primary_email = dbFunctions.getDBField(config_file, server_name, user_email, "primaryEmail")
        secondary_email = dbFunctions.getDBField(config_file, server_name, user_email, "secondaryEmail")

        to_emails = []
        if notify_email == "Primary":
            to_emails.append(primary_email)
        elif notify_email == "Secondary":
            to_emails.append(secondary_email)
        elif notify_email == "Both":
            to_emails.extend([primary_email, secondary_email])

        if to_emails:
            emailFunctions.sendSubscriptionRemoved(config_file, to_emails, user_email, dry_run)

        # Discord notification
        notify_discord = dbFunctions.getDBField(config_file, server_name, user_email, "notifyDiscord")
        primary_discord = dbFunctions.getDBField(config_file, server_name, user_email, "primaryDiscordId")
        secondary_discord = dbFunctions.getDBField(config_file, server_name, user_email, "secondaryDiscordId")

        to_discord = []
        if notify_discord == "Primary":
            to_discord.append(primary_discord)
        elif notify_discord == "Secondary":
            to_discord.append(secondary_discord)
        elif notify_discord == "Both":
            to_discord.extend([primary_discord, secondary_discord])

        if to_discord:
            discordFunctions.sendDiscordSubscriptionRemoved(config_file, to_discord, user_email, dry_run)

        logging.info(f"Notifications sent for user '{user_email}' removal from server '{server_name}'.")
    except Exception as e:
        logging.error(f"Error notifying user '{user_email}': {e}")


# Example Function for Authentication
def authenticate_to_plex_account(username, password, server_name):
    """
    Authenticate to Plex and connect to the specified server.

    Args:
        username (str): Plex account username.
        password (str): Plex account password.
        server_name (str): Name of the Plex server.

    Returns:
        PlexServer: Authenticated Plex server instance, or None on failure.
    """
    try:
        account = MyPlexAccount(username, password)
        return account.resource(server_name).connect()
    except Exception as e:
        logging.error(f"Error authenticating to Plex server '{server_name}': {e}")
        return None
