#!/usr/bin/python3

# Workaround to prevent errors with grequests
from gevent import monkey as curious_george
curious_george.patch_all(thread=False, select=False)

import asyncio
import datetime
import json

import discord
import tools
import hypixel
import minecraft


def log(text):
    print('{0}: {1}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), text))


class ChamosBot(discord.Client):
    async def on_ready(self):
        activity = discord.Activity(name='>bw', type=discord.ActivityType.listening, start=datetime.datetime.now())
        await client.change_presence(status=discord.Status.online, activity=activity)
        log('Logged in as {0}, id {1}'.format(self.user.name, self.user.id))

    async def on_message(self, message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return

        if message.content.startswith('>bw'):
            parameters = message.content.split()[1:]
            usernames = [x for x in parameters if x[0] != '-']
            table = hypixel.get_bedwars_table(usernames)
            table_message = await message.channel.send(f'```{table}```')
            
            rxns = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']
            gamemodes = ['eight_one', 'eight_two', 'four_three', 'four_four']

            for rxn in rxns:
                await table_message.add_reaction(rxn)
            
            def check(reaction, user):
                return user == message.author and str(reaction.emoji) in rxns and table_message.id == reaction.message.id

            try:
                reaction, user = await self.wait_for('reaction_add', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                pass
            else:
                gamemode = gamemodes[rxns.index(str(reaction.emoji))]
                new_table = hypixel.get_bedwars_table(usernames, gamemode=gamemode)
                await table_message.edit(content=f'```{new_table}```')

            log(f'Sent table for {" ".join(usernames)}')
        
        elif message.content.startswith('>sw'):
            parameters = message.content.split()[1:]
            usernames = [x for x in parameters if x[0] != '-']
            table = hypixel.get_bedwars_table(usernames, stat_class=hypixel.SkywarsPlayer)
            table_message = await message.channel.send(f'```{table}```')

            log(f'Sent SkyWars table for {" ".join(usernames)}')

        elif message.content.startswith('>fkdr'):
            parameters = message.content.split()[1:]
            usernames = [x for x in parameters if x[0] != '-']
            players = [hypixel.HystatsBedwarsPlayer(x) for x in usernames]
            await message.channel.send('\n'.join([x.get_yesterday_fkdr() for x in players]))
        
        elif message.content.startswith('>skin'):
            parameters = message.content.split()[1:]
            usernames = [x for x in parameters if x[0] != '-']
            players = [minecraft.PlayerSkin(x) for x in usernames]

            for player in players:
                rxn = '📁'
                current = await message.channel.send(player.get_full())
                await current.add_reaction(rxn)

                def check(reaction, user):
                    return user == message.author and str(reaction.emoji) == '📁' and current.id == reaction.message.id


                try:
                    reaction, user = await self.wait_for('reaction_add', timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    pass
                else:
                    new_link = player.get_download()
                    await current.edit(content=new_link)
            
        elif message.content.startswith('>art'):
            await message.channel.send('https://cdn.discordapp.com/attachments/688748355702095900/717805575395868772/sun_2.png')

    async def on_member_join(self, member):
        guild = member.guild
        if guild.system_channel is not None:
            to_send = 'Welcome {0.mention} to {1.name}!'.format(member, guild)
            await guild.system_channel.send(to_send)


discord_secret = json.loads(open('credentials.json').read())['discord-token']

client = ChamosBot()
client.run(discord_secret)
