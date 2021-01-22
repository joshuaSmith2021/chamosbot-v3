import datetime
import json

import requests

import iksm
import tools

BASE_URL = 'http://localhost:8080'

with open('data/splatoon2/gamemodes.json') as file_:
    GAMEMODES = json.loads(file_.read())

with open('data/splatoon2/rulesets.json') as file_:
    RULESETS = json.loads(file_.read())

COLORS = [0xfa5a00, 0x2851f6, 0xc800dc, 0xf93195, 0x00c8b4, 0xa0cc0a]

class Stage:
    name = None
    sid = None

    def __init__(self, data):
        self.name = data['name']
        self.sid = data['id']

    def __str__(self):
        return self.name


class Weapon:
    wid = None
    name = None
    image = None
    thumbnail = None

    def __init__(self, entry):
        self.wid = entry['id']
        self.name = entry['name']
        self.image = entry['image']
        self.thumbnail = entry['thumbnail']

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


def get_salmon_weapons(weapons):
    result = []
    for weapon in weapons:
        key = [x for x in weapon.keys() if x not in ['image', 'id', 'name', 'thumbnail']][0]
        result.append(Weapon(weapon[key]))

    return result


class Match:
    def __init__(self, data):
        self.result = data['my_team_result']['key']
        self.stage = Stage(data['stage'])
        self.ruleset = data['rule']['name']
        self.gamemode = data['game_mode']['name']
        self.symbol = 'W' if self.result == 'victory' else 'L'
        self.weapon = data['player_result']['player']['weapon']['name']

    def __str__(self):
        return f'{self.result.capitalize()}: {self.gamemode} {self.ruleset} on {str(self.stage)}'

    def __repr__(self):
        return self.__str__()


class GenericScheduleItem:
    start = None
    end = None

    def time_range(self):
        time_format = '%b %-d %-I:%M%p'
        return f'{self.start.strftime(time_format)} – {self.end.strftime(time_format)}'

    def start_string(self):
        time_format = '%-I:%M%p'
        return f'{self.start.strftime(time_format)} {tools.get_today_tomorrow(self.start)}'

    def duration_remaining(self):
        now = datetime.datetime.now()
        if now < self.start:
            return (self.start - now, 'until start')
        elif now < self.end:
            return (self.end - now, 'remaining')
        else:
            return (now - self.end, 'ago')

    def __init__(self, entry):
        self.start = datetime.datetime.fromtimestamp(int(entry['start_time']))
        self.end = datetime.datetime.fromtimestamp(int(entry['end_time']))


class ScheduleItem(GenericScheduleItem):
    ruleset = None
    gamemode = None
    stages = []

    def __init__(self, entry):
        self.ruleset = (entry['rule']['name'], entry['rule']['key'])
        self.gamemode = (entry['game_mode']['name'], entry['game_mode']['key'])
        self.stages = [Stage(x) for x in [entry['stage_a'], entry['stage_b']]]
        self.start = datetime.datetime.fromtimestamp(int(entry['start_time']))
        self.end = datetime.datetime.fromtimestamp(int(entry['end_time']))

    def __str__(self):
        gamemode = self.gamemode[0]
        ruleset = self.ruleset[0]
        stages = ' & '.join(map(str, self.stages))
        time_range = self.time_range()
        return f'{gamemode} {ruleset} on {stages} at {time_range}'

    def __repr__(self):
        return self.__str__()


class SalmonScheduleItem(GenericScheduleItem):
    weapons = None
    stage = None

    def __init__(self, entry):
        self.stage = entry['stage']['name']
        self.start = datetime.datetime.fromtimestamp(int(entry['start_time']))
        self.end = datetime.datetime.fromtimestamp(int(entry['end_time']))
        self.weapons = get_salmon_weapons(entry['weapons'])

    def __str__(self):
        time_range = self.time_range()
        weapon_string = tools.english_list(map(str, self.weapons))
        return f'Salmon Run on {self.stage} with the {weapon_string} at {time_range}'

    def __repr__(self):
        return self.__str__()


def get_schedule():
    url = f'{BASE_URL}/splatoon/schedule'
    req = requests.get(url)
    return req.json()


def get_salmon_schedule():
    url = f'{BASE_URL}/splatoon/salmonrun/schedule'
    req = requests.get(url)
    return req.json()


def combine_gamemodes(schedule):
    all_entries = []
    for gamemode in schedule.values():
        all_entries += gamemode

    return all_entries


def search_schedule(focus, *args, schedule_=None):
    schedule = get_schedule() if schedule_ is None else schedule_
    entries = schedule if schedule_ is not None else [ScheduleItem(x) for x in combine_gamemodes(schedule)]
    filtered = list(sorted(filter(lambda x: focus(x) in args, entries), key=lambda x: x.start))
    return filtered


def get_current_stages():
    schedule = get_schedule()
    current_stages = []

    for gamemode in GAMEMODES:
        current_entries = schedule[gamemode['id']]
        first = [ScheduleItem(x) for x in current_entries][0]
        current_stages.append(first)

    return current_stages


def stages_notification(blocks, include_gamemode=True, include_ruleset=False,
                        include_stage=False, include_time=True, return_sentence=True):
    with open('data/splatoon2/gamemodes.json') as file_:
        gamemodes = json.loads(file_.read())

    result = []

    for gamemode in gamemodes:
        current_blocks = [x for x in blocks if gamemode['id'] == x.gamemode[1]]

        if len(current_blocks) == 0:
            continue

        mode_result = []
        if include_gamemode:
            mode_result.append(gamemode['name'])

        for block in current_blocks:
            current_string = []
            if include_ruleset:
                current_string.append(block.ruleset[0])

            if include_stage:
                current_string.append(f"on {' and '.join(map(str, block.stages))}")

            if include_time:
                current_string.append(f'at {block.start_string()}')

            mode_result.append(' '.join(current_string))

        result.append(': '.join(mode_result))

    return '. '.join(result) if return_sentence else result


def get_schedule_objects():
    return {key: value for key, value in [(mode, [ScheduleItem(x) for x in entries]) for mode, entries in get_schedule().items()]}


def call_splatoon_api(path, user):
    url = f'https://app.splatoon2.nintendo.net{path}'
    cookie = user['cookie']
    req = requests.get(url, cookies={'iksm_session': cookie})

    if 'code' in req.json().keys():
        # cookie expired, get a new one
        nickname, new_cookie = iksm.get_cookie(user['session_token'])

        iksm.update_users({user['uid']: {'cookie': new_cookie}})

        req = requests.get(url, cookies={'iksm_session': new_cookie})

    return req.json()


def get_matches(results):
    return [Match(x) for x in results['results']]


def get_weapons(matches):
    return [x.weapon for x in matches]


def get_results(user):
    return call_splatoon_api('/api/results', user)


def get_records(user):
    return call_splatoon_api('/api/records', user)


def get_ranks(records):
    modes = [
        ('Splat Zones', 'udemae_zones'),
        ('Tower Control', 'udemae_tower'),
        ('Rainmaker', 'udemae_rainmaker'),
        ('Clam Blitz', 'udemae_clam')
    ]

    return {display: records['records']['player'][key]['name'] for display, key in modes}


if __name__ == '__main__':
    pass

