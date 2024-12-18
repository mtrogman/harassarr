# harassarr.py
import logging, sys, os, schedule, time, argparse, discord, mysql.connector, subprocess, signal
from discord.ext import commands
from datetime import datetime, timedelta
from modules import dbFunctions, configFunctions, plexFunctions, validateFunctions, emailFunctions, discordFunctions

# Constants
CONFIG_FILE = "/config/config.yml"
USER_DATA_FILE = "/config/userData.csv"
LOG_FILE = "/config/harassarr.log"

# Set up Discord bot
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Set up logging
if not os.path.exists(LOG_FILE):
    open(LOG_FILE, "w").close()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a"),
    ],
)

logger = logging.getLogger("Harassarr")

# Signal handling for graceful shutdown
def signal_handler(sig, frame):
    logger.info("Gracefully shutting down Harassarr...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# Helper functions (Need to be moved to modules after I refactor)
def validate_config(config_file):
    """Validate configuration file."""
    logger.debug(f"Validating configuration file: {config_file}")
    try:
        config = configFunctions.getConfig(config_file)
        required_keys = ["database", "log"]
        for key in required_keys:
            if key not in config:
                raise KeyError(f"Missing required configuration key: {key}")
        logger.info("Configuration validation successful.")
        return config
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)


def connect_to_database(db_config):
    """Establish database connection."""
    logger.debug("Establishing database connection...")
    try:
        connection = mysql.connector.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
        )
        logger.info("Database connection established successfully.")
        return connection
    except mysql.connector.Error as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)


def delete_old_logs(log_file, retention_days):
    """Delete old log entries."""
    logger.debug(f"Deleting logs older than {retention_days} days.")
    try:
        with open(log_file, "r+") as file:
            lines = file.readlines()
            file.seek(0)
            for line in lines:
                try:
                    log_date_str = line.split(" - ", 1)[0]
                    log_date = datetime.strptime(log_date_str, "%Y-%m-%d %H:%M:%S,%f")
                    if datetime.now() - log_date <= timedelta(days=retention_days):
                        file.write(line)
                except ValueError:
                    logger.warning("Skipping invalid log line: %s", line.strip())
            file.truncate()
    except Exception as e:
        logger.error(f"Error deleting old logs: {e}")


def check_inactive_users_on_discord(config, dryrun):
    """Check and remove roles for inactive Discord users."""
    logger.debug("Checking inactive users on Discord.")
    try:
        if os.path.exists(USER_DATA_FILE):
            os.remove(USER_DATA_FILE)
            logger.info(f"Deleted existing {USER_DATA_FILE}")
        else:
            logger.info(f"{USER_DATA_FILE} does not exist, skipping deletion.")

        subprocess.run(["python", "supplemental/userDetail.py"])

        if not os.path.exists(USER_DATA_FILE):
            raise FileNotFoundError(f"{USER_DATA_FILE} not found.")

        discord_user_data = discordFunctions.readCsv(USER_DATA_FILE)
        db_config = config["database"]
        plex_configs = [config[key] for key in config if key.startswith("PLEX-")]

        for plex_config in plex_configs:
            server_name = plex_config["serverName"]
            role = plex_config["role"]
            inactive_users = dbFunctions.getUsersByStatus(
                user=db_config["user"],
                password=db_config["password"],
                host=db_config["host"],
                database=db_config["database"],
                status="Inactive",
                serverName=server_name,
            )

            for user in inactive_users:
                discord_ids = ["primaryDiscordId", "secondaryDiscordId"]
                for discord_id in discord_ids:
                    if discord_id in user:
                        discord_id_value = user[discord_id]
                        for user_data in discord_user_data:
                            if user_data["discord_id"] == discord_id_value:
                                roles = user_data["roles"]
                                if role.lower() in map(str.lower, roles):
                                    logger.warning(
                                        f"Inactive user {user['primaryDiscord']} still has role {role}"
                                    )
                                    discordFunctions.removeRole(
                                        CONFIG_FILE, discord_id_value, role, dryrun=dryrun
                                    )
    except Exception as e:
        logger.error(f"Error checking inactive users on Discord: {e}")


def check_users_end_date(config, dryrun):
    """Check if users are near or past their end dates."""
    logger.debug("Checking users' end dates.")
    db_config = config["database"]
    connection = connect_to_database(db_config)
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM users WHERE status = 'Active'")
        active_users = cursor.fetchall()
        today = datetime.now().date()

        for user in active_users:
            end_date = user["endDate"]
            if not end_date:
                continue

            days_left = (end_date - today).days
            if days_left < 0:
                logger.warning(
                    f"User {user['primaryEmail']} is past their subscription end date."
                )
                # Additional removal logic here
            elif days_left < 7:
                logger.info(
                    f"User {user['primaryEmail']} has {days_left} days remaining."
                )
                # Additional notification logic here
    except Exception as e:
        logger.error(f"Error checking users' end dates: {e}")
    finally:
        cursor.close()
        connection.close()


# Daily run logic
def daily_run(args, dryrun):
    logger.info("Starting Daily Run")
    config = validate_config(CONFIG_FILE)

    try:
        delete_old_logs(LOG_FILE, config["log"].get("retention", 90))
        check_inactive_users_on_discord(config, dryrun)
        check_users_end_date(config, dryrun)
        logger.info("Daily Run completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during the daily run: {e}")
        sys.exit(1)


# Main entry point
def main():
    parser = argparse.ArgumentParser(description="Harassarr Script")
    parser.add_argument("--dryrun", action="store_true", help="Run in dry-run mode")
    parser.add_argument(
        "-time", metavar="time", type=str, help="Daily run time in HH:MM format"
    )
    args = parser.parse_args()

    dryrun = args.dryrun
    run_time = None

    if args.time:
        try:
            run_time = datetime.strptime(args.time, "%H:%M").time()
        except ValueError:
            logger.error("Invalid time format. Use HH:MM.")
            sys.exit(1)

    if run_time:
        logger.info(f"Scheduled daily run at {run_time}.")
        schedule.every().day.at(run_time.strftime("%H:%M")).do(daily_run, args, dryrun)
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Unexpected error in scheduled task: {e}")
                sys.exit(1)
    else:
        logger.info("Running daily tasks immediately.")
        daily_run(args, dryrun)


if __name__ == "__main__":
    main()
