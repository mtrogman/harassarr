# discordFunctions.py
import discord
import logging
import modules.dbFunctions as dbFunctions
import modules.configFunctions as configFunctions

async def send_discord_message(bot, user_id, message):
    try:
        user = await bot.fetch_user(user_id)
        await user.send(message)
        logging.info(f"Message sent to {user_id} on Discord")
    except discord.errors.Forbidden:
        logging.error(f"Permission error: Could not send a message to {user_id} on Discord")

async def send_discord_notification(bot, server_name, user_email, message):
    notify_discord = dbFunctions.getNotifyDiscord(configFile, server_name, user_email)

    if notify_discord == 'Primary':
        user_discord = dbFunctions.getPrimaryDiscord(configFile, server_name, user_email)
        await send_discord_message(bot, user_discord, message)
    elif notify_discord == 'Secondary':
        user_discord = dbFunctions.getSecondaryDiscord(configFile, server_name, user_email)
        await send_discord_message(bot, user_discord, message)
    elif notify_discord == 'Both':
        primary_discord = dbFunctions.getPrimaryDiscord(configFile, server_name, user_email)
        secondary_discord = dbFunctions.getSecondaryDiscord(configFile, server_name, user_email)
        await send_discord_message(bot, primary_discord, message)
        await send_discord_message(bot, secondary_discord, message)
    else:
        # Do nothing if notify_discord is 'None'
        pass