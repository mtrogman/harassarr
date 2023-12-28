# discordFunctions.py
import discord
import logging
import modules.dbFunctions as dbFunctions
import modules.configFunctions as configFunctions

def sendDiscordMessage(token, userId, message):
    # Initialize the Discord client
    client = discord.Client()

    @client.event
    async def on_ready():
        user = client.get_user(userId)
        if user:
            await user.send(message)
        await client.close()

    # Run the client with the provided bot token
    client.run(token)

def sendSubscriptionReminder(configFile, primaryDiscord, daysLeft):
    # Retrieve the Discord configuration from the config file
    config = configFunctions.getConfig(configFile)
    discordConfig = config.get('discord', {})

    # Extract Discord configuration values
    token = discordConfig.get('token', '')

    # Check if any required values are missing
    if not token or not primaryDiscord:
        raise ValueError("Discord configuration is incomplete. Please check your config file.")

    # Create the message for subscription reminder
    message = f"Dear User,\n\nYour subscription is set to expire in {daysLeft} days. " \
              f"Please contact us if you wish to continue your subscription. " \
              f"\n\nBest regards,\nThe TrogPlex Team"

    # Send the Discord message
    sendDiscordMessage(token, primaryDiscord, message)
    logging.info("Subscription reminder sent to Discord.")

def sendSubscriptionRemoved(configFile, primaryDiscord):
    # Retrieve the Discord configuration from the config file
    config = configFunctions.getConfig(configFile)
    discordConfig = config.get('discord', {})

    # Extract Discord configuration values
    token = discordConfig.get('token', '')

    # Check if any required values are missing
    if not token or not primaryDiscord:
        raise ValueError("Discord configuration is incomplete. Please check your config file.")

    # Create the message for subscription removal
    message = f"Your subscription has been removed from Trog's Plex. " \
              f"Please contact us if you wish to continue your subscription."

    # Send the Discord message
    sendDiscordMessage(token, primaryDiscord, message)
    logging.info("Subscription removal notification sent to Discord.")