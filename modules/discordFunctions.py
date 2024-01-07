# discordFunctions.py
import logging
import asyncio
import discord
from discord.ext import commands
from discord import Embed
import modules.configFunctions as configFunctions


def getDiscordConfig(config):
    return config.get('discord', {})


def getReminderSubject(config):
    discordConfig = getDiscordConfig(config)
    return discordConfig.get('reminderSubject', "<YOUR NAME>'s Plex Subscription Reminder - {daysLeft} Days Left")


def getReminderBody(config):
    discordConfig = getDiscordConfig(config)
    return discordConfig.get('reminderBody', "Dear User,\n\nYour subscription for email: {primaryEmail} is set to expire in {days_left} days. Please contact us if you wish to continue your subscription by replying to this message or contact <YOUR NAME> on Discord (https://discord.gg/XXXXXXXX).\n\nBest regards,\n<YOUR NAME>")


def getRemovalSubject(config):
    discordConfig = getDiscordConfig(config)
    return discordConfig.get('removalSubject', "<YOUR NAME>'s Plex Subscription Ended")


def getRemovalBody(config):
    discordConfig = getDiscordConfig(config)
    return discordConfig.get('removalBody', "Dear User,\n\nYour subscription for email: {primaryEmail} has ended on <YOUR NAME>'s Plex. Please contact us if you wish to continue your subscription by replying to this message or contact <YOUR NAME> on Discord (https://discord.gg/XXXXXXXX).\n\nBest regards,\n<YOUR NAME>")


def sendDiscordMessage(configFile, toUser, subject, body):
    config = configFunctions.getConfig(configFile)
    discord_config = getDiscordConfig(config)
    botToken = discord_config.get('token', '')

    if not botToken:
        logging.error("Discord bot token is missing in the configuration.")
        return

    # Create a Bot instance with intents
    intents = discord.Intents.default()
    intents.messages = True
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        user = await bot.fetch_user(toUser[0])
        embed = Embed(title=f"**{subject}**", description=body, color=discord.Colour.blue())
        try:
            await user.send(embed=embed)
        except discord.errors.Forbidden as e:
            logging.warning(f"Failed to send message to {user.name}#{user.discriminator}: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred for {user.name}: {e}")
        finally:
            await bot.close()

    bot.run(botToken)


def sendDiscordSubscriptionReminder(configFile, toUser, primaryEmail, daysLeft, dryrun):
    config = configFunctions.getConfig(configFile)
    subject = getReminderSubject(config).format(daysLeft=daysLeft)
    body = getReminderBody(config).format(primaryEmail=primaryEmail, daysLeft=daysLeft)
    if dryrun:
        logging.info(f"DISCORD NOTIFICATION ({primaryEmail} SKIPPED DUE TO DRYRUN")
    else:
        sendDiscordMessage(configFile, toUser, subject, body)


def sendDiscordSubscriptionRemoved(configFile, toUser, primaryEmail, dryrun):
    config = configFunctions.getConfig(configFile)
    subject = getRemovalSubject(config)
    body = getRemovalBody(config).format(primaryEmail=primaryEmail)
    if dryrun:
        logging.info(f"DISCORD NOTIFICATION ({primaryEmail} SKIPPED DUE TO DRYRUN")
    else:
        sendDiscordMessage(configFile, toUser, subject, body)


async def getUserData(configFile):
    config = configFunctions.getConfig(configFile)
    discord_config = getDiscordConfig(config)
    botToken = discord_config.get('token', '')

    if not botToken:
        logging.error("Discord bot token is missing in the configuration.")
        return

    # Create a Bot instance with intents
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

    @bot.event
    async def on_ready():
        print("I am running on " + bot.user.name)
        print("With the ID: " + bot.user.id)
        print('Bot is ready to be used')
        guildId = discord_config.get('guildId', '')
        guild = bot.get_guild(int(guildId[-18:]))

        if guild:
            members = guild.members
            userData = [['Discord Username', 'Discord User ID', 'Roles']]

            # Iterate through members and add data to user_data
            for member in members:
                roles = ', '.join([role.name for role in member.roles if role.name != '@everyone'])
                userInfo = [member.name, member.id, roles]
                userData.append(userInfo)

            print("At the end")
            print(userData)
            return userData
        else:
            print(f"Guild with ID {guildId} not found.")
            return None

    bot.run(botToken)