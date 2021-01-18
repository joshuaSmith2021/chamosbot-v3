import datetime
import re
from subprocess import check_output

import pytz

import matrix

Table = matrix.Table

def get_localized_times(datetime_):
    '''Returns a list with localized datetimes for certain timezones.
    [0]: Los Angeles
    [1]: New York
    '''
    timezones = map(pytz.timezone, ['America/Los_Angeles', 'America/New_York'])
    return [x.localize(datetime_) for x in timezones]


def format_number(num):
    if num == '-':
        return num
    elif int(num) == float(num):
        # It is an integer
        return '{:,}'.format(num)
    else:
        # It is a float:
        return '{:,.2f}'.format(num)


def get_stat(dataset, stat):
    data = dataset
    for key in stat.split('.'):
        data = data[key]

    return data.replace(',', '')


def sort_table(table, index):
    def key(x):
        try:
            return float(x[index])
        except ValueError:
            # This happens for the first column, which
            # is text. To make it stay first, set it to
            # infinity
            return float('inf')

    zipped = list(zip(*table))
    zipped.sort(key=key, reverse=True)

    result = matrix.Table(just='right')

    for i in range(len(zipped[0])):
        result.append([x[i] for x in zipped])

    return result


def parse_monthly_data(string):
    # For HyStats. Parses the variable for monthly stats
    result = []
    start = string.index('[')
    data = re.sub(r'\s|\[|\]', '', string[start:-1])
    for element in data.split(',{'):
        element = element.strip('}{')
        date, fkdr, kdr, wlr = map(lambda x: x.split(':')[1], element.split(','))
        fkdr, kdr, wlr = map(float, [fkdr, kdr, wlr])
        date = date.strip('\'')
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
        result.append((date, fkdr, kdr, wlr))
    
    result.sort(key=lambda x: x[0], reverse=True)

    return result


def english_list(_list):
    _list = [str(x) for x in _list]
    if len(_list) == 0:
        return ''
    elif len(_list) == 1:
        return _list[0]
    elif len(_list) == 2:
        return ' and '.join(_list)
    else:
        body = ', '.join(_list[:-1])
        result = f'{body}, and {_list[-1]}'
        return result


def get_today_tomorrow(date):
    one_day = datetime.timedelta(1)
    now = datetime.datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + one_day
    two_days = tomorrow + one_day

    if date >= today and date < tomorrow:
        return 'today'
    elif date >= tomorrow and date < two_days:
        return 'tomorrow'
    elif date <= today and today - date <= one_day:
        return 'yesterday'
    else:
        return date.strftime('on %B %-d')


def format_delta(delta, desired_format):
    time = int(delta.total_seconds())
    desired_format = desired_format.upper()
    result = []
    if 'D' in desired_format:
        days = time // 86400
        time -= days * 86400
        result.append('{}d'.format(days))
    if 'H' in desired_format:
        hours = time // 3600
        time -= hours * 3600
        result.append('{}h'.format(hours))
    if 'M' in desired_format:
        minutes = time // 60
        time -= minutes * 60
        result.append('{}m'.format(minutes))
    if 'S' in desired_format:
        seconds = time
        time -= seconds
        result.append('{}s'.format(seconds))

    return ' '.join([x for x in result if re.match(r'^0[dhms]', x) is None])


def get_ip_address():
    ifconfig = check_output(['ifconfig']).decode('utf-8').rstrip()
    sections = ifconfig.split('\n\n')
    search = re.search(r'(inet) (192.168.1.\d+)', sections[-1])
    return search.group(2)


if __name__ == '__main__':
    # for tz in [x for x in pytz.all_timezones if 'America' in x]:
    #     print(tz)
    # exit()
    now = datetime.datetime.now()
    localized_times = get_localized_times(now)
    print(localized_times)
    tf = '%-I:%M'
    print(' '.join([x.strftime(tf) for x in localized_times]))
