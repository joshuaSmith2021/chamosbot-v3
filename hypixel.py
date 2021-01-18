from gevent import monkey as curious_george
curious_george.patch_all(thread=False, select=False)

import asyncio
import datetime
import json
import re
import sys
from abc import ABC, abstractmethod

import grequests
import requests
from bs4 import BeautifulSoup, SoupStrainer
import matrix
import mojang
import tools

curious_george.patch_all(thread=False, select=False)

API_KEY = json.loads(open('credentials.json').read())['apikey']

class HypixelUsernameError(mojang.MinecraftUsernameError):
    pass


def stat_table(players):
    if issubclass(type(players), HypixelPlayer):
        players = [players]
    elif type(players) == type([]):
        pass
    else:
        print(type(players))
        raise ValueError(f'players must be a HypixelPlayer or a list of HypixelPlayers. Got a {type(players)} instead')

    datasets = [x.get_stats() for x in players]

    result = matrix.Table(just='right')
    result.append([''] + [x.username for x in players])

    rows = players[0].rows()

    for stat in rows:
        row = []

        stat_name = stat.split('#')[1]
        row.append(stat_name)

        for i in range(len(players)):
            dataset = datasets[i]

            plugged = re.sub(r'\^[^^$]+\.[^^$]+\$', lambda x: tools.get_stat(dataset, x[0][1:-1]), stat.split('#')[0])

            try:
                value = tools.format_number(eval(plugged))
            except ZeroDivisionError:
                value = '-'
            except SyntaxError:
                if '!' in plugged:
                    value = plugged.replace('!', '').rstrip()
                else:
                    value = '-'

            row.append(value)

        result.append(row)

    return result


class HypixelPlayer(mojang.Player, ABC):
    plancke_page = None

    # All subclasses must have this method defined. It should return
    # the name of the game as it appears in the DOM of a plancke stat
    # page.
    @abstractmethod
    def game(self):
        return None

    # Called in self.get_stats. Some gamemodes have an extra table
    # row or something that needs to be adjusted, so this function
    # cleans up data later on. By default, it does not do anything.
    def clean_table(self, table):
        return table

    # Like self.clean_table, this method is called in self.get_stats
    # to handle minigame-specific things. By default, it does nothing.
    def add_stats(self, stats, soup, domid):
        return stats

    # Updates self.plancke_page
    def update_page(self):
        url = f'https://plancke.io/hypixel/player/stats/{self.uuid}'
        req = requests.get(url)
        self.plancke_page = req.text
    
    # Gets the user's plancke page if it is still None, then returns
    # the plancke page
    def get_page(self):
        if self.plancke_page is None:
            self.update_page()
        
        return self.plancke_page

    def get_stats(self):
        game = self.game()
        domid = f'stat_panel_{game}'

        strainer = SoupStrainer('div', {'id': domid})
        soup = BeautifulSoup(self.get_page(), 'html.parser', parse_only=strainer)
        stat_div = soup.find('div', {'id': domid})
        stat_table = stat_div.findChild('table')

        table = []
        for row in [x for x in stat_table.descendants if x.name == 'tr']:
            cells = [x for x in row.strings if x != '\n']
            if len(cells) == 0:
                continue
            
            table.append(cells)
        
        table = self.clean_table(table)

        stats = {}
        keys = table[0]
        for row in table[1:]:
            zipped = list(zip(keys, row))
            gamemode = zipped[0][1]
            current = {}
            for key, stat in zipped[1:]:
                if key not in current.keys():
                    current[key] = stat
                else:
                    current[f'Final {key}'] = stat
            
            stats[gamemode] = current
        
        stats = self.add_stats(stats, soup, domid)

        return stats
    
    def get_recent_games(self):
        url = f'https://api.hypixel.net/recentGames?key={API_KEY}&uuid={self.uuid}'
        req = requests.get(url)
        res = req.json()
        games = res['games']
        return [x for x in games if x['gameType'] == self.game().upper()]


class SkywarsPlayer(HypixelPlayer):
    def game(self):
        return 'SkyWars'
    
    def rows(self):
        return ['^Solo Normal.Wins$ + ^Solo Insane.Wins$ #Solo Wins',
                '^Team Normal.Wins$ + ^Team Insane.Wins$ #Team Wins']


class BedwarsPlayer(HypixelPlayer):
    def game(self):
        return 'BedWars'
    
    def rows(self):
        return ['^Overall.Level$ #Bedwars Level', '^Solo.Wins$ #Solo Wins', 
                '^Doubles.Wins$ #Doubles Wins', '^3v3v3v3.Wins$ #3v3v3v3 Wins', 
                '^4v4v4v4.Wins$ #4v4v4v4 Wins', '^4v4.Wins$ #4v4 Wins',
                '^Overall.Wins$ #Total Wins', 
                '^Overall.Wins$ / (^Overall.Wins$ + ^Overall.Losses$) #Win Rate', 
                '^Overall.Kills$ #Kills', '^Overall.K/D$ #K/D',
                '^Overall.Final Kills$ #Final Kills', 
                '^Overall.Final K/D$ #Final K/D', 
                '^Overall.Kills$ + ^Overall.Final Kills$ #Total Kills']
    
    def clean_table(self, table):
        return table[1:]
    
    def add_stats(self, stats, soup, domid):
        stat_div = soup.find('div', {'id': domid})
        bw_list = stat_div.find('ul', class_='list-unstyled')
        bw_level = 0
        for li in bw_list.children:
            if re.match('<li><b>Level:</b> [0-9,]+</li>', str(li)):
                bw_level = re.search('[0-9,]+', str(li)).group()
        
        stats['Overall']['Level'] = bw_level

        return stats


class SoloBedwarsPlayer(BedwarsPlayer):
    def rows(self):
        return ['^Solo.Wins$ #Solo Wins',
                '^Solo.Wins$ / (^Solo.Wins$ + ^Solo.Losses$) #Win Rate',
                '^Solo.Kills$ #Kills', '^Solo.K/D$ #K/D',
                '^Solo.Final Kills$ #Final Kills', '^Solo.Final K/D$ #Final K/D',
                '^Solo.Kills$ + ^Solo.Final Kills$ #Total Kills']


class DoublesBedwarsPlayer(BedwarsPlayer):
    def rows(self):
        return ['^Doubles.Wins$ #Doubles Wins',
                '^Doubles.Wins$ / (^Doubles.Wins$ + ^Doubles.Losses$) #Win Rate',
                '^Doubles.Kills$ #Kills', '^Doubles.K/D$ #K/D',
                '^Doubles.Final Kills$ #Final Kills', '^Doubles.Final K/D$ #Final K/D',
                '^Doubles.Kills$ + ^Doubles.Final Kills$ #Total Kills']


class ThreesBedwarsPlayer(BedwarsPlayer):
    def rows(self):
        return ['^3v3v3v3.Wins$ #3v3v3v3 Wins',
                '^3v3v3v3.Wins$ / (^3v3v3v3.Wins$ + ^3v3v3v3.Losses$) #Win Rate',
                '^3v3v3v3.Kills$ #Kills', '^3v3v3v3.K/D$ #K/D',
                '^3v3v3v3.Final Kills$ #Final Kills', '^3v3v3v3.Final K/D$ #Final K/D',
                '^3v3v3v3.Kills$ + ^3v3v3v3.Final Kills$ #Total Kills']


class FoursBedwarsPlayer(BedwarsPlayer):
    def rows(self):
        return ['^4v4v4v4.Wins$ #4v4v4v4 Wins',
                '^4v4v4v4.Wins$ / (^4v4v4v4.Wins$ + ^4v4v4v4.Losses$) #Win Rate',
                '^4v4v4v4.Kills$ #Kills', '^4v4v4v4.K/D$ #K/D',
                '^4v4v4v4.Final Kills$ #Final Kills', '^4v4v4v4.Final K/D$ #Final K/D',
                '^4v4v4v4.Kills$ + ^4v4v4v4.Final Kills$ #Total Kills']


class HystatsBedwarsPlayer(mojang.Player):
    hystats_page = None
    registered = None

    def update_page(self):
        url = f'https://hystats.net/player/bedwars/{self.uuid}'
        req = requests.get(url)
        self.hystats_page = req.text

        stat_search = re.search(r'monthlypvpdata = \[[^;]+;', self.hystats_page)
        if stat_search is not None:
            self.registered = True
        else:
            self.registered = False
    
    def get_page(self):
        if self.hystats_page is None:
            self.update_page()
        
        return self.hystats_page

    def get_monthly_data(self):
        page = self.get_page()
        data_pattern = r'monthlypvpdata = \[[^;]+;'
        if re.search(data_pattern, page) is not None:
            data = re.search(data_pattern, page).group()
            return tools.parse_monthly_data(data)
    
    def get_yesterday_fkdr(self):
        # Returns a two-item tuple, index 0 being the datetime for the day
        # during which the FKDR was taken, index 1 being the fkdr of the day

        page = self.get_page()

        if not self.registered:
            page = self.get_page()
            wait_pattern = r'Note: We will first fetch your data in <b>\dmin\(s\)'
            wait_message = re.search(wait_pattern, page)
            wait_string = None

            if wait_message is not None:
                wait_time = re.search(r'\d+', wait_message.group())
                wait = wait_time.group()
                wait_string = f' {self.username}\'s HyStats page will be updated in {wait} minutes. From there, it will be updated every 24 hours.'
            else:
                wait_string = ''

            return f'{self.username} does not have data available on HyStats.{wait_string}'

        data = self.get_monthly_data()
        try:
            date, fkdr = data[1][:2]
        except IndexError:
            return f'{self.username} does not have Bedwars data recorded on HyStats yet. Stats are updated every 24 hours.'

        date_string = date.strftime('%A, %B %d, %Y')
        date_string = re.sub(r'0[0-9],', lambda x: x.group()[1:], date_string)
        return f'On {date_string}, {self.username} had a {fkdr} FKDR.'


def get_bedwars_table(usernames, gamemode=None, stat_class=None):
    players = []
    errors  = []
    for username in usernames:
        try:
            if stat_class is not None:
                players.append(stat_class(username))
                continue

            if gamemode == 'eight_one':
                players.append(SoloBedwarsPlayer(username))
            elif gamemode == 'eight_two':
                players.append(DoublesBedwarsPlayer(username))
            elif gamemode == 'four_three':
                players.append(ThreesBedwarsPlayer(username))
            elif gamemode == 'four_four':
                players.append(FoursBedwarsPlayer(username))
            else:
                players.append(BedwarsPlayer(username))

        except mojang.MinecraftUUIDError:
            errors.append(f'{username} is too long to be a username, and it is not a valid UUID.')
        except mojang.MinecraftUsernameError:
            errors.append(f'{username} is not a valid Minecraft username.')


    urls = [f'https://plancke.io/hypixel/player/stats/{player.uuid}' for player in players]
    reqs = (grequests.get(u) for u in urls)
    ress = grequests.map(reqs)

    for i in range(len(players)):
        players[i].plancke_page = ress[i].text

    table = stat_table(players)
    table = tools.sort_table(table, 1)

    result = str(table)

    if len(errors) > 0:
        result += '\n\n{0}'.format('\n'.join(errors))

    return result


if __name__ == '__main__':
    while True:
        players = [BedwarsPlayer(x) for x in input('> ').split(' ')]
        print(stat_table(players))

