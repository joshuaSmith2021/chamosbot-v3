from gevent import monkey as curious_george
curious_george.patch_all(thread=False, select=False)

import json
import requests

import mojang

API_KEY = json.loads(open('credentials.json').read())['apikey']


if __name__ == '__main__':
    player = mojang.Player(input('Enter player name\n> '))
    uuid = player.uuid

    url = f'https://api.hypixel.net/recentGames?key={API_KEY}&uuid={uuid}'
    req = requests.get(url)

    print(req.text)