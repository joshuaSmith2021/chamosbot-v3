# Workaround to prevent errors with grequests
from gevent import monkey as curious_george
curious_george.patch_all(thread=False, select=False)

import json

import discord
from discord.ext import commands

import chamosbot_commands as cbc

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='>', intents=intents)

[bot.add_cog(cog()) for cog in cbc.COGS]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    bot.help_command.cog = cbc.Support()
    activity = discord.Activity(name='>help', type=discord.ActivityType.listening)
    await bot.change_presence(activity=activity)


@bot.event
async def on_member_join(member):
    if member.guild.id == 801310380898516992:
        await member.guild.system_channel.send(f'hi <@{member.id}> please respect the mods and be careful not to play any videos sent by <@494211951757492226> or <@798043978648911872>')


with open('credentials.json') as file_:
    private_data = json.loads(file_.read())
    DISCORD_TOKEN = private_data['discord-token']

bot.run(DISCORD_TOKEN)

