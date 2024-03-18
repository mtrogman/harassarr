# discordFunctions.py
import logging
import csv
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
    discordConfig = getDiscordConfig(config)
    botToken = discordConfig.get('token', '')

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


def sendDiscordSubscriptionReminder(configFile, toUser, primaryEmail, daysLeft, fourk, streamCount, oneM, threeM, sixM, twelveM, dryrun):
    config = configFunctions.getConfig(configFile)
    subject = getReminderSubject(config).format(daysLeft=daysLeft)
    body = getReminderBody(config).format(
        primaryEmail=primaryEmail, daysLeft=daysLeft, streamCount=streamCount, fourk=fourk, oneM=oneM, threeM=threeM, sixM=sixM, twelveM=twelveM)
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


def removeRole(configFile, discordUserId, roleName, dryrun):
    config = configFunctions.getConfig(configFile)
    discordConfig = getDiscordConfig(config)
    botToken = discordConfig.get('token', '')

    if not botToken:
        logging.error("Discord bot token is missing in the configuration.")
        return

    # Create a Bot instance with intents
    intents = discord.Intents.default()
    intents.messages = True
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        user = await bot.fetch_user(discordUserId)
        guildId = int(discordConfig.get('guildId', ''))

        guild = bot.get_guild(guildId)

        if user:
            # Use fetch_member instead of get_member
            member = await guild.fetch_member(user.id)

            if member:
                role = discord.utils.get(guild.roles, name=roleName)

                if role:
                    if dryrun:
                        logging.info(f"DISCORD ROLE REMOVAL {roleName} SKIPPED FOR {member.name} ({member.id} DUE TO DRYRUN")
                    else:
                        await member.remove_roles(role)
                        logging.info(f"Removed role {roleName} from user {member.name} ({member.id})")
                else:
                    logging.error(f"Role {roleName} not found")
            else:
                logging.error(f"Member {discordUserId} not found in the guild")
        else:
            logging.error(f"User {discordUserId} not found")

        await bot.close()

    bot.run(botToken)

def readCsv(userDataFile):
    users = []
    with open(userDataFile, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            # Assuming the CSV format is [Discord Name, Discord User ID, Roles]
            users.append({
                'name': row[0],
                'discord_id': row[1],
                'roles': [] if len(row) < 3 else [role.strip() for role in row[2].split(',')]
            })
    return users