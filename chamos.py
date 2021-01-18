# Workaround to prevent errors with grequests
from gevent import monkey as curious_george
curious_george.patch_all(thread=False, select=False)

import json

import discord
from discord.ext import commands

import chamosbot_commands as cbc

bot = commands.Bot(command_prefix='>')

[bot.add_cog(cog()) for cog in cbc.COGS]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    activity = discord.Activity(name='>help', type=discord.ActivityType.listening)
    await bot.change_presence(activity=activity)


with open('credentials.json') as file_:
    private_data = json.loads(file_.read())
    DISCORD_TOKEN = private_data['discord-token']

bot.run(DISCORD_TOKEN)

