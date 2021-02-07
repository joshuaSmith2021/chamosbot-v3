import json
import re

import requests

def get_user_stats(username):
    request = requests.get(f'https://api.chess.com/pub/player/{username}/stats')

    if request.status_code == 404:
        # Invalid user
        return None
        # raise ValueError(f'{username} is not a valid username.')

    data = request.json()
    return data


def get_elos(user_stats):
    result = {}

    for key in filter(lambda x: re.match(r'chess_\w+', x), user_stats.keys()):
        title = key[6:]
        result[title] = user_stats[key]

    return result


def record_string(data):
    return '/'.join([str(data['record'][x]) for x in ['win', 'loss', 'draw']])


def build_embed(embed, user_data):
    '''Create a Discord embed with user data displayed.
    embed should be a Discord embed object.
    user_data should be a dict returned from get_elos
    '''

    for key, data in user_data.items():
        if re.match(r'chess_\w+', key) is None:
            continue

        title = key[6:]

        lines = []
        lines.append(f'Rating: {data["last"]["rating"]}')
        lines.append(f'Best Rating: {data["best"]["rating"]}')
        lines.append(f'Record (W/L/D): {record_string(data)}')

        embed.add_field(name=title.title(), value='\n'.join(lines), inline=True)

    return embed


if __name__ == '__main__':
    user = get_user_stats('magnuscarlsen')
    # print(get_elos(user))
    build_embed(None, user)

