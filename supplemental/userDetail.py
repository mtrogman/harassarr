#!/usr/bin/env python3
import discord
from discord.ext import commands
import sys
import os
import csv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules import configFunctions
from modules import discordFunctions

configFile = "./config/config.yml"
config = configFunctions.getConfig(configFile)
discordConfig = discordFunctions.getDiscordConfig(config)
botToken = discordConfig.get('token', '')

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Define a command to export user information to CSV
@bot.event
async def on_ready():
    # Get all members from the server
    guildId = int(discordConfig.get('guildId', ''))
    channelId = int(discordConfig.get('channelId', ''))
    guild = bot.get_guild(guildId)

    if guild:
        members = guild.members

        # Prepare CSV data
        discordUsers = [['Discord Username', 'Discord User ID', 'Roles']]

        # Iterate through members and add data to CSV
        for member in members:
            roles = ', '.join([role.name for role in member.roles if role.name != '@everyone'])
            userData = [member.name, member.id, roles]
            discordUsers.append(userData)

        # Write CSV data to a file
        with open('userData.csv', 'w', newline='') as csv_file:
            csvWriter = csv.writer(csv_file)
            csvWriter.writerows(discordUsers)
        await bot.close()

bot.run(botToken)
