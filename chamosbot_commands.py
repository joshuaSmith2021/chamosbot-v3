import datetime
import re
import statistics

from discord.ext import commands

import hypixel
import iksm
import splatoon
import tools

class Bedwars(commands.Cog):
    '''Commands for Minecraft Hypixel Bedwars
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

                await ctx.channel.send('Current Rotation ({0} remaining)\n{1}'.format(tools.format_delta(remaining_time, 'hm'), '\n'.join(current_stage_strings)))

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

                def make_stage_string(stage):

                    remaining, status = stage.duration_remaining()

                    return ' '.join([
                        stage.gamemode[0],
                        stage.ruleset[0],
                        ' '.join(map(str, stage.stages)),
                        f'({tools.format_delta(remaining, "hm")}',
                        f'{status})',
                    ])

                stage_strings = map(make_stage_string, schedule)
                result = '\n'.join(stage_strings)

                await ctx.channel.send(result if len(result) < 2000 else f'The resulting message is too long! ({len(result)} characters) Try making your request more specific by adding filters.')

    @commands.command(aliases=['sr', 'salmon'])
    async def salmonrun(self, ctx):
        '''Get Salmon Run schedule.
        '''
        schedule = [splatoon.GenericScheduleItem(x) for x in splatoon.get_salmon_schedule()['schedules']]

        def make_shift_string(shift):
            tf = '%-I:%M %p'
            time_range = ' – '.join([f'{x.strftime(tf)} {tools.get_today_tomorrow(x)}' for x in [shift.start, shift.end]])
            remaining, status = shift.duration_remaining()
            return f'{time_range} ({tools.format_delta(remaining, "dhm")} {status})'

        shift_strings = '\n'.join(map(make_shift_string, schedule))
        message = f'Upcoming Salmon Runs\n{shift_strings}\nAll times are shown in Los Angeles Time.'

        await ctx.channel.send(message)

    @commands.command()
    async def register(self, ctx):
        '''Receive a Nintendo login link through DM's to link your Nintendo account to your Discord account.
        '''
        await ctx.author.send(iksm.log_in(ctx))

    @commands.command()
    async def link(self, ctx, nintendo_url):
        '''Link your Nintendo account to your Discord with the link you received with >register.
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

        if (aid := ctx.author.id) not in user_ids:
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
            results = splatoon.get_past_games(user['cookie'])
            results['matches'] = [splatoon.Match(x) for x in results['results']]
            user_data[i]['results'] = results

        async def get_form(x):
            text = ''.join([x.symbol for x in x['results']['matches'][:5]])
            streak_pattern = f'^{text[0]}+'
            streak = len(re.search(streak_pattern, text).group())
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

        result = tools.Table(just='right')
        for title, func in rows:
            result.append([title, *[(await func(x)) for x in user_data]])

        await ctx.channel.send(f'```{str(result)}```')


class Development(commands.Cog):
    '''Commands for chamosbot development
    '''

    @commands.command()
    async def ip(self, ctx):
        '''Get location of chamosbot server.
        '''

        result = tools.get_ip_address().split('.')[-1]
        await ctx.channel.send(result)


COGS = [Bedwars, Splatoon, Development]

