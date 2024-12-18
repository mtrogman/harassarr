import logging, csv, discord
from discord.ext import commands
from discord import Embed
import modules.configFunctions as configFunctions

# Configure logging
logger = logging.getLogger("DiscordFunctions")

# Helper Functions
def get_discord_config(config):
    """
    Retrieve the Discord configuration from the global configuration.

    Args:
        config (dict): The global configuration dictionary.

    Returns:
        dict: The Discord configuration dictionary.
    """
    return config.get('discord', {})


def get_message_template(config, key, default_template):
    """
    Retrieve a message template from the Discord configuration.

    Args:
        config (dict): The global configuration dictionary.
        key (str): The template key in the Discord configuration.
        default_template (str): The default template to use if the key is missing.

    Returns:
        str: The retrieved or default message template.
    """
    discord_config = get_discord_config(config)
    return discord_config.get(key, default_template)


async def send_discord_embed(bot, user_id, subject, body):
    """
    Send a Discord embed message to a specific user.

    Args:
        bot (commands.Bot): The Discord bot instance.
        user_id (int): The Discord user ID to send the message to.
        subject (str): The subject of the message.
        body (str): The body of the message.

    Returns:
        None
    """
    try:
        user = await bot.fetch_user(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found.")
            return

        embed = Embed(title=f"**{subject}**", description=body, color=discord.Colour.blue())
        await user.send(embed=embed)
        logger.info(f"Sent message to user ID {user_id}: {subject}")
    except discord.Forbidden:
        logger.warning(f"Permission denied: Unable to send message to user ID {user_id}.")
    except Exception as e:
        logger.error(f"Unexpected error while sending message to user ID {user_id}: {e}")


# Main Functions
def send_discord_message(config_file, user_id, subject, body):
    """
    Send a Discord message to a user.

    Args:
        config_file (str): Path to the configuration file.
        user_id (int): The Discord user ID to send the message to.
        subject (str): The subject of the message.
        body (str): The body of the message.

    Returns:
        None
    """
    config = configFunctions.getConfig(config_file)
    discord_config = get_discord_config(config)
    bot_token = discord_config.get('token')

    if not bot_token:
        logger.error("Discord bot token is missing in the configuration.")
        return

    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"Bot logged in as {bot.user}. Sending message...")
        await send_discord_embed(bot, user_id, subject, body)
        await bot.close()

    bot.run(bot_token)


def send_discord_subscription_reminder(config_file, user_id, primary_email, days_left, fourk, stream_count, one_m, three_m, six_m, twelve_m, dry_run):
    """
    Send a subscription reminder message via Discord.

    Args:
        config_file (str): Path to the configuration file.
        user_id (int): The Discord user ID to send the message to.
        primary_email (str): The user's primary email.
        days_left (int): Days left until subscription ends.
        fourk (str): Whether the subscription includes 4K.
        stream_count (int): Number of allowed streams.
        one_m (float): Price for a 1-month subscription.
        three_m (float): Price for a 3-month subscription.
        six_m (float): Price for a 6-month subscription.
        twelve_m (float): Price for a 12-month subscription.
        dry_run (bool): If True, log the action instead of sending the message.

    Returns:
        None
    """
    config = configFunctions.getConfig(config_file)
    subject = get_message_template(config, 'reminderSubject', "<YOUR NAME>'s Plex Subscription Reminder - {daysLeft} Days Left").format(daysLeft=days_left)
    body = get_message_template(config, 'reminderBody', (
        "Dear User,\n\nYour subscription for email: {primaryEmail} is set to expire in {daysLeft} days. "
        "Please contact us if you wish to continue your subscription by replying to this message or "
        "contact <YOUR NAME> on Discord (https://discord.gg/XXXXXXXX).\n\nBest regards,\n<YOUR NAME>"
    )).format(primaryEmail=primary_email, daysLeft=days_left, streamCount=stream_count, fourk=fourk, oneM=one_m, threeM=three_m, sixM=six_m, twelveM=twelve_m)

    if dry_run:
        logger.info(f"Dry run: Subscription reminder for {primary_email} skipped.")
    else:
        send_discord_message(config_file, user_id, subject, body)


def send_discord_subscription_removed(config_file, user_id, primary_email, dry_run):
    """
    Send a subscription removal notification via Discord.

    Args:
        config_file (str): Path to the configuration file.
        user_id (int): The Discord user ID to send the message to.
        primary_email (str): The user's primary email.
        dry_run (bool): If True, log the action instead of sending the message.

    Returns:
        None
    """
    config = configFunctions.getConfig(config_file)
    subject = get_message_template(config, 'removalSubject', "<YOUR NAME>'s Plex Subscription Ended")
    body = get_message_template(config, 'removalBody', (
        "Dear User,\n\nYour subscription for email: {primaryEmail} has ended on <YOUR NAME>'s Plex. "
        "Please contact us if you wish to continue your subscription by replying to this message or "
        "contact <YOUR NAME> on Discord (https://discord.gg/XXXXXXXX).\n\nBest regards,\n<YOUR NAME>"
    )).format(primaryEmail=primary_email)

    if dry_run:
        logger.info(f"Dry run: Subscription removal for {primary_email} skipped.")
    else:
        send_discord_message(config_file, user_id, subject, body)


def read_csv(user_data_file):
    """
    Read a CSV file containing Discord user data.

    Args:
        user_data_file (str): Path to the CSV file.

    Returns:
        list: List of dictionaries with user data.
    """
    users = []
    try:
        with open(user_data_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                users.append({
                    'name': row[0],
                    'discord_id': row[1],
                    'roles': [] if len(row) < 3 else [role.strip() for role in row[2].split(',')]
                })
        logger.info(f"Successfully read {len(users)} users from {user_data_file}.")
    except Exception as e:
        logger.error(f"Error reading CSV file {user_data_file}: {e}")
    return users
