import datetime
import json
import random
import re
import statistics
import uuid

import discord
from discord.ext import commands

import hypixel
import iksm
import splatoon
import tools

class Support(commands.Cog):
    '''Commands for help and support from developers.
    '''

    @commands.command(aliases=['report', 'bug'])
    async def issue(self, ctx):
        '''Contact developer.
        '''
        await ctx.author.send('Please DM <@580157651548241940> with details about your error, suggestion, etc.')


class Bedwars(commands.Cog):
    '''Commands for Minecraft Hypixel Bedwars.
    '''

    @commands.command(aliases=['bw'])
    async def bedwars(self, ctx, *usernames):
        '''Get Bedwars table with stats for each username.
        '''

        async with ctx.channel.typing():
            table = hypixel.get_bedwars_table(usernames)
            await ctx.channel.send(f'```{table}```')


class Splatoon(commands.Cog):
    '''Commands for Splatoon 2
    '''

    aliases = {
        'ranked': 'gachi',
        'turf': 'turf_war',
        'blitz': 'clam_blitz',
        'tower': 'tower_control',
        'zones': 'splat_zones'
    }

    @commands.command()
    async def stages(self, ctx, *args):
        '''Get current Splatoon 2 stages.
        args is as many filters as desired to find the gamemode you want. Valid filters:

        GAMEMODES
        regular: pick out regular stages
        ranked: pick out ranked stages
        league: pick out league stages

        RULESETS
        turf: pick out turf wars
        zones: pick out splat zones
        rainmaker: pick out rainmaker
        blitz: pick out clam blitz
        tower: pick out tower control
        '''

        async with ctx.channel.typing():
            schedule = splatoon.get_schedule_objects()

            if len(args) == 0:
                keys = map(lambda x: x['id'], splatoon.GAMEMODES)

                stage_formatting = {
                    'include_gamemode': True,
                    'include_ruleset': True,
                    'include_stage': True,
                    'include_time': False,
                    'return_sentence': False
                }

                current_stage_strings = splatoon.stages_notification([schedule[x][0] for x in keys], **stage_formatting)
                remaining_time = schedule['regular'][0].end - datetime.datetime.now()

                embed = discord.Embed(title='Current Rotation', description=f'{tools.format_delta(remaining_time, "hm")} remaining', color=random.choice(splatoon.COLORS))
                [embed.add_field(name=mode, value=details, inline=True) for mode, details in [x.split(': ') for x in current_stage_strings]]
                await ctx.channel.send(embed=embed)

            else:
                schedule = splatoon.combine_gamemodes(schedule)
                keys = [self.aliases.get(x, x) for x in args]

                stage_formatting = {
                    'include_gamemode': True,
                    'include_ruleset': True,
                    'include_stage': True,
                    'include_time': True,
                    'return_sentence': False
                }

                if len(gamemodes := set(['regular', 'gachi', 'league']) & set(keys)) > 0:
                    schedule = splatoon.search_schedule(lambda x: x.gamemode[1], *gamemodes, schedule_=schedule)

                if len(rulesets := set(['turf_war', 'splat_zones', 'tower_control', 'rainmaker', 'clam_blitz']) & set(keys)):
                    schedule = splatoon.search_schedule(lambda x: x.ruleset[1], *rulesets, schedule_=schedule)

                if len(schedule) == 0:
                    await ctx.channel.send('No results found. Please try making your request less specific by removing filters.')
                    return

                def make_stage_strings(stage):

                    remaining, status = stage.duration_remaining()

                    return (
                        f'{stage.gamemode[0]}\n{stage.ruleset[0]}',
                        '\n'.join([
                            '\n'.join(map(str, stage.stages)),
                            f'({tools.format_delta(remaining, "hm")} {status})'
                        ])
                    )

                stage_strings = map(make_stage_strings, schedule)

                embed = discord.Embed(title='Upcoming Stages', color=random.choice(splatoon.COLORS))
                [embed.add_field(name=mode, value=details, inline=True) for mode, details in stage_strings]

                await ctx.channel.send(embed=embed)

    @commands.command(aliases=['sr', 'salmon'])
    async def salmonrun(self, ctx):
        '''Get Salmon Run schedule.
        '''
        salmon_schedule = splatoon.get_salmon_schedule()

        weapons = {str(x['start_time']): [y['weapon' if 'weapon' in y.keys() else 'coop_special_weapon']['name'] for y in x['weapons']] for x in salmon_schedule['details']}
        schedule = [splatoon.GenericScheduleItem(x) for x in salmon_schedule['schedules']]

        def make_shift_string(shift):
            tf = '%-I:%M %p'
            time_range = ' – '.join([f'{x.strftime(tf)} {tools.get_today_tomorrow(x)}' for x in [shift.start, shift.end]])
            remaining, status = shift.duration_remaining()
            return (time_range, f'{tools.format_delta(remaining, "dhm")} {status}')

        embed = discord.Embed(title="Upcoming Salmon Runs", color=random.choice(splatoon.COLORS))
        embed.set_footer(text="All times are shown in Los Angeles time.")

        for block in schedule:
            time_range, status = make_shift_string(block)
            weapon_list = weapons.get(str(block.start_stamp), None)
            if weapon_list is not None:
                status = '\n'.join(['Weapons:', *weapon_list, status])

            embed.add_field(name=time_range, value=status, inline=False)

        await ctx.channel.send(embed=embed)

    @commands.command()
    async def register(self, ctx):
        '''Receive a Nintendo login link through DM's to link your Nintendo account to your Discord account.
        For help: https://youtu.be/4RD-3L7_vQI
        '''
        await ctx.author.send(iksm.log_in(ctx))

    @commands.command()
    async def link(self, ctx, nintendo_url):
        '''Link your Nintendo account to your Discord with the link you received with >register.
        For help: https://youtu.be/4RD-3L7_vQI
        '''
        await ctx.author.send(iksm.check_link(ctx, nintendo_url))

    @commands.command()
    async def results(self, ctx, *args):
        '''Get past results for users.
        args is multiple arguments separated by spaces. Each argument can be a:
        Discord user mention (@user): If the mentioned user has linked their Nintendo account to Discord
        Integer: The amount of games to count. The default is 5 if no number is given.
        '''
        mention_pattern = r'<@!?(\d+)>'
        mention_matches = [x for x in args if re.match(mention_pattern, x) is not None]
        user_ids = [int(re.match(mention_pattern, x).group(1)) for x in mention_matches]

        match_args = [x for x in args if x.isnumeric()]
        match_count = 5 if len(match_args) == 0 else match_args[0]

        if (aid := ctx.author.id) not in user_ids and len(user_ids) == 0:
            user_ids.append(aid)

        unregistered_users = []
        user_data = []
        for uid in user_ids:
            data = iksm.get_user(uid)
            if data is None:
                unregistered_users.append(uid)
                continue

            user_data.append(dict(uid=uid, **data))

        for i, data in enumerate(user_data):
            if data.get('cookie', None) is None:
                del user_data[i]
                unregistered_users.append(data['uid'])

        if len(user_data) == 0:
            await ctx.channel.send('None of the given users have linked their accounts with chamosbot. See `>help register` for more details.')
            return

        for i, user in enumerate(user_data):
            results = splatoon.get_results(user)
            results['matches'] = [splatoon.Match(x) for x in results['results']]
            user_data[i]['results'] = results

        async def get_form(x):
            symbols = ''.join([x.symbol for x in x['results']['matches']])
            text = symbols[:5]
            streak_pattern = f'^{text[0]}+'
            streak = len(re.search(streak_pattern, symbols).group())
            return f'{text} ({streak}{text[0]} streak)'

        async def get_usernames(x):
            return (await ctx.bot.fetch_user(int(x['uid']))).name

        async def get_favorite_weapon(x):
            weapons = [x.weapon for x in x['results']['matches']]
            mode = statistics.mode(weapons)
            count = f'{weapons.count(mode)}/{len(weapons)}'
            return f'{mode} ({count})'

        rows = [
            ('', get_usernames),
            ('Current Form', get_form),
            ('Favorite Weapon', get_favorite_weapon)
        ]

        if len(user_data) == 1:
            user = user_data[0]
            embed = discord.Embed(title=(await get_usernames(user)), description='Recent Stats', color=random.choice(splatoon.COLORS))
            for field, func in rows[1:]:
                embed.add_field(name=field, value=(await func(user)), inline=True)

            await ctx.channel.send(embed=embed)
            return

        result = tools.Table(just='right')
        for title, func in rows:
            result.append([title, *[(await func(x)) for x in user_data]])

        await ctx.channel.send(f'```{str(result)}```')

    @commands.command(aliases=['ranking', 'ranks'])
    async def rank(self, ctx, *args):
        '''Get ranks for users.
        args is multiple arguments separated by spaces. Each argument must be a:
        Discord user mention (@user): If the mentioned user has linked their Nintendo account to Discord
        If multiple users are given, the response is formatted in a table with all of their ranks side-by-side.
        If one user is given, the response is a prettier embed with their rankings.
        '''
        mention_pattern = r'<@!?(\d+)>'
        mention_matches = [x for x in args if re.match(mention_pattern, x) is not None]
        user_ids = [int(re.match(mention_pattern, x).group(1)) for x in mention_matches]

        if (aid := ctx.author.id) not in user_ids and len(user_ids) == 0:
            user_ids.append(aid)

        unregistered_users = []
        user_data = []
        for uid in user_ids:
            data = iksm.get_user(uid)
            if data is None:
                unregistered_users.append(uid)
                continue

            user_data.append(dict(uid=uid, **data))

        for i, data in enumerate(user_data):
            if data.get('cookie', None) is None:
                del user_data[i]
                unregistered_users.append(data['uid'])

        if len(user_data) == 0:
            await ctx.channel.send('None of the given users have linked their accounts with chamosbot. See `>help register` for more details.')
            return

        for i, user in enumerate(user_data):
            records = splatoon.get_records(user)
            user_data[i]['ranks'] = splatoon.get_ranks(records)

        if len(user_data) == 1:
            # Only one user given, send pretty embed
            user = user_data[0]
            embed = discord.Embed(title=(await ctx.bot.fetch_user(int(user['uid']))).name, description='Splatoon 2 Ranking', color=random.choice(splatoon.COLORS))
            for mode in user['ranks'].keys():
                embed.add_field(name=mode, value=user['ranks'][mode], inline=True)

            await ctx.channel.send(embed=embed)
            return

        async def get_username(x):
            return (await ctx.bot.fetch_user(int(x['uid']))).name

        def get_rank(x, key):
            return x['ranks'][key]

        result = tools.Table(just='left')

        result.append(['', *[(await get_username(x)) for x in user_data]])
        
        for mode in user_data[0]['ranks'].keys():
            row = [mode]
            for user in user_data:
                row.append(get_rank(user, mode))

            result.append(row)

        await ctx.channel.send(f'```{str(result)}```')

    @commands.command()
    async def salmonrank(self, ctx, *args):
        '''IN DEVELOPMENT

        Get Salmon Run ranks for users.
        args is multiple arguments separated by spaces. Each argument must be a:
        Discord user mention (@user): If the mentioned user has linked their Nintendo account to Discord
        If multiple users are given, the response is formatted in a table with all of their ranks side-by-side.
        If one user is given, the response is a prettier embed with their rankings.
        '''

        mention_pattern = r'<@!?(\d+)>'
        mention_matches = [x for x in args if re.match(mention_pattern, x) is not None]
        user_ids = [int(re.match(mention_pattern, x).group(1)) for x in mention_matches]

        if (aid := ctx.author.id) not in user_ids and len(user_ids) == 0:
            user_ids.append(aid)

        unregistered_users = []
        user_data = []
        for uid in user_ids:
            data = iksm.get_user(uid)
            if data is None:
                unregistered_users.append(uid)
                continue

            user_data.append(dict(uid=uid, **data))

        for i, data in enumerate(user_data):
            if data.get('cookie', None) is None:
                del user_data[i]
                unregistered_users.append(data['uid'])

        if len(user_data) == 0:
            await ctx.channel.send('None of the given users have linked their accounts with chamosbot. See `>help register` for more details.')
            return

        for i, user in enumerate(user_data):
            results = splatoon.get_salmon_results(user)
            with open('data/responses/salmon-results.json', 'w') as f:
                f.write(json.dumps(results))


class Development(commands.Cog):
    '''Commands for chamosbot development
    '''

    @commands.command()
    async def ip(self, ctx):
        '''Get location of chamosbot server.
        '''

        result = tools.get_ip_address().split('.')[-1]
        await ctx.channel.send(result)

    @commands.command()
    async def uuid(self, ctx):
        '''Generate a UUID using Python's uuid.uuid4 function.
        '''
        await ctx.channel.send(str(uuid.uuid4()))


COGS = [Bedwars, Splatoon, Development, Support]

