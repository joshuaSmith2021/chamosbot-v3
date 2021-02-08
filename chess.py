import datetime
import json
import re

from bs4 import BeautifulSoup
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


def pogchamp_schedule_to_csv():
    with open('data/pogchamps/pogchamps3table.html') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    rows = soup.findAll('tr', {'class': ['standings_odd_row', 'standings_even_row']})

    csv = [
        ('Subject', 'Start Date', 'Start Time', 'End Time', 'Description')
    ]

    for row in rows:
        cells = [x.text for x in row.findChildren()]
        if '-' in cells:
            # Skip the pre-match hype event for now
            continue

        day, dow, start, end, group, mnum, p1, p2 = cells
        csv.append((
            f'{p1} vs {p2}',
            f'02/{day.split()[1]}/2021',
            f'{start} {"AM" if start[:2] == "11" else "PM"}',
            f'{end} {"AM" if end[:2] == "11" else "PM"}',
            f'{group}: {mnum}'
        ))

    return '\n'.join(map(lambda x: ','.join(x), csv))


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
    # build_embed(None, user)
    with open('data/pogchamps/poghamps3schedule.csv', 'w') as f:
        schedule = pogchamp_schedule_to_csv()
        f.write(schedule)

