# Some functions for the Mojang API

# import grequests and requests
import grequests
import requests

import datetime
import json

class MinecraftUUIDError(ValueError):
    pass


class MinecraftUsernameError(ValueError):
    pass


class Player:
    # Essential variables
    username = None
    uuid = None

    # Vars to be used in called methods
    names = None

    def __init__(self, id):
        if len(id) > 16:
            # It is a uuid, get the username as well
            self.uuid = id
            try:
                self.username = get_player_from_uuid(id)['name']
            except MinecraftUUIDError as err:
                raise err

        else:
            # It is a username, get the uuid
            self.username = id
            try:
                req = get_uuid_from_player(id)
                self.uuid = req[0]['id']
                self.username = req[0]['name']
            except IndexError:
                raise MinecraftUsernameError(f'{id} is not a valid username')

    def name_history(self):
        if self.names is None:
            req_url = f'https://api.mojang.com/user/profiles/{self.uuid}/names'
            req = requests.get(req_url)
            res = req.json()

            self.names = [(res[0]['name'], None)]
            for name in res[1:]:
                self.names.append((name['name'], name['changedToAt'] // 1000))

        return self.names

    def __str__(self):
        return f'{self.username} {self.uuid}'


def get_uuid_from_player(names):
    # If names is just a string of one name, convert it to a list
    if type(names) == ''.__class__:
        names = [names]

    url = 'https://api.mojang.com/profiles/minecraft'
    req = requests.post(url, json=names)
    return req.json()


def get_players_from_uuids(uuids):
    # Gets the usernames for each uuid provided
    if type(uuids) == ''.__class__:
        uuids = [uuids]

    urls = [f'https://sessionserver.mojang.com/session/minecraft/profile/{uuid}' for uuid in uuids]
    reqs = (grequests.get(u) for u in urls)
    ress = grequests.map(reqs)
    return [x.json() for x in ress]


def get_player_from_uuid(uuid):
    # Gets the player data for a uuid
    url = f'https://sessionserver.mojang.com/session/minecraft/profile/{uuid}'
    req = requests.get(url)
    try:
        return req.json()
    except json.decoder.JSONDecodeError:
        raise MinecraftUUIDError(f'{uuid} is not a valid UUID')


if __name__ == '__main__':
    # youtubers = ['gamerboy80', 'Purpled', 'RaguSpaghetti', 'FishermanGamer']
    # uuids = [x['id'] for x in get_uuid_from_player(youtubers)]
    # print(json.dumps(uuids))
    player = Player('parcerx')
    names = player.name_history()
    for name in names:
        try:
            print(f'Switched to {name[0]} {datetime.datetime.fromtimestamp(name[1])}')
        except TypeError as err:
            print(f'Original name: {name[0]}')

