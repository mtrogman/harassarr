#!/usr/bin/env python3
import discord
from discord.ext import commands
import sys
import os
import csv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules import configFunctions
from modules import discordFunctions

configFile = "../config/config.yml"
config = configFunctions.getConfig(configFile)
discord_config = discordFunctions.getDiscordConfig(config)
botToken = discord_config.get('token', '')

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Define a command to export user information to CSV
@bot.command(name='export_users')
async def export_users(ctx):
    # Get all members from the server
    members = ctx.guild.members

    # Prepare CSV data
    discordUsers = [['Discord Username', 'Discord User ID', 'Roles']]

    # Iterate through members and add data to CSV
    for member in members:
        roles = ', '.join([role.name for role in member.roles if role.name != '@everyone'])
        user_data = [member.name, member.id, roles]
        discordUsers.append(user_data)

    # Write CSV data to a file
    with open('user_data.csv', 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerows(discordUsers)

    # Send the CSV file to the Discord channel
    await ctx.send(file=discord.File('user_data.csv'))
    await bot.close()
    exit(0)

bot.run(botToken)
