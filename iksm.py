###########################################################
#                                                         #
# From https://github.com/frozenpandaman/splatnet2statink #
# I did not make this file, but I am using it to allow    #
# bot users to login to the Nintendo API to see their own #
# stats.                                                  #
#                                                         #
# Some modifications were made to the original file in    #
# order to adapt it to the Discord bot flow.              #
#                                                         #
###########################################################

# eli fessler
# clovervidia
from __future__ import print_function
from builtins import input
import requests, json, re, sys
import os, base64, hashlib
import uuid, time, random, string

import firestore_handler as firestore

session = requests.Session()
version = "unknown"
data_file = 'data/users/nintendo_keys.json'

# place config.txt in same directory as script (bundled or not)
if getattr(sys, 'frozen', False):
    app_path = os.path.dirname(sys.executable)
elif __file__:
    app_path = os.path.dirname(__file__)
    config_path = os.path.join(app_path, "config.txt")

def user_exists(aid):
    aid = str(aid)
    existing_documents = firestore.list_documents('users')
    doc_ids = [x['name'].split('/')[-1] for x in existing_documents['documents']]
    return aid in doc_ids


def save_user(aid, **kwargs):
    aid = str(aid)
    if user_exists(aid):
        # User already has document, so patch the existing one
        request = firestore.update_document('users', aid, firestore.make_fields(kwargs))
    else:
        # User does not have a document, so create one
        request = firestore.create_document('users', aid, firestore.make_fields(kwargs))

    return request


def get_user(aid):
    document = firestore.get_document('users', str(aid))
    result = {}
    try:
        for key, pair in document['fields'].items():
            value = list(pair.values())[0]
            result[key] = value
    except KeyError:
        # Data does not exist
        return None

    return result


def update_users(new_data):
    old_data = json.loads(open(data_file).read())

    for user, data in new_data.items():
        for key, value in data.items():
            try:
                old_data[user][key] = value
            except KeyError:
                # Create new dict for user
                old_data[user] = data

    with open(data_file, 'w') as file_:
        file_.write(json.dumps(old_data))

def log_in(ctx, ver='1.5.7'):
    '''Logs in to a Nintendo Account and returns a session_token.'''

    global version
    version = ver

    auth_state = base64.urlsafe_b64encode(os.urandom(36))

    auth_code_verifier = base64.urlsafe_b64encode(os.urandom(32))
    auth_cv_hash = hashlib.sha256()
    auth_cv_hash.update(auth_code_verifier.replace(b"=", b""))
    auth_code_challenge = base64.urlsafe_b64encode(auth_cv_hash.digest())

    app_head = {
        'Host':                      'accounts.nintendo.com',
        'Connection':                'keep-alive',
        'Cache-Control':             'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent':                'Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36',
        'Accept':                    'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8n',
        'DNT':                       '1',
        'Accept-Encoding':           'gzip,deflate,br',
    }

    body = {
        'state':                               auth_state,
        'redirect_uri':                        'npf71b963c1b7b6d119://auth',
        'client_id':                           '71b963c1b7b6d119',
        'scope':                               'openid user user.birthday user.mii user.screenName',
        'response_type':                       'session_token_code',
        'session_token_code_challenge':        auth_code_challenge.replace(b"=", b""),
        'session_token_code_challenge_method': 'S256',
        'theme':                               'login_form'
    }

    url = 'https://accounts.nintendo.com/connect/1.0.0/authorize'
    r = session.get(url, headers=app_head, params=body)

    post_login = r.history[0].url

    message_lines = []

    message_lines.append("Navigate to this URL in your browser:")
    message_lines.append(post_login)
    message_lines.append("Log in, right click the \"Select this account\" button, copy the link address, and use the following command:")
    message_lines.append("`>link <your url>`")
    message_lines.append('For help: https://youtu.be/4RD-3L7_vQI')

    user_data = {
        'auth_code_verifier': auth_code_verifier.decode('utf-8')
    }

    save_user(str(ctx.author.id), **user_data)

    return '\n'.join(message_lines)

def check_link(ctx, url):
    if not user_exists(ctx.author.id):
        return 'You don\'t seem to have a data file on our servers. Please use `>register`.'

    user_data = get_user(str(ctx.author.id))

    auth_code_verifier = user_data.get('auth_code_verifier', None)
    if auth_code_verifier is None:
        return 'You don\'t have auth_code_verifier in your data. Please use `>register`'

    try:
        use_account_url = url
        session_token_code = re.search('de=(.*)&', use_account_url)
        session_token = get_session_token(session_token_code.group(1), auth_code_verifier)
    except AttributeError:
        return "Malformed URL. Please try again."
    except KeyError: # session_token not found
        return 'The URL has expired. Please log out and back into your Nintendo Account and try again.'

    user_data['session_token'] = session_token

    nickname, cookie = get_cookie(session_token)
    user_data['cookie'] = cookie
    user_data['nickname'] = nickname

    save_user(ctx.author.id, **user_data)

    return f'Hello, {nickname}! Your account is now linked and you can use account-specific commands.'

def get_session_token(session_token_code, auth_code_verifier):
    '''Helper function for log_in().'''

    app_head = {
        'User-Agent':      'OnlineLounge/1.10.0 NASDKAPI Android',
        'Accept-Language': 'en-US',
        'Accept':          'application/json',
        'Content-Type':    'application/x-www-form-urlencoded',
        'Content-Length':  '540',
        'Host':            'accounts.nintendo.com',
        'Connection':      'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }

    body = {
        'client_id':                   '71b963c1b7b6d119',
        'session_token_code':          session_token_code,
        'session_token_code_verifier': auth_code_verifier.replace("=", "")
    }

    url = 'https://accounts.nintendo.com/connect/1.0.0/api/session_token'

    r = session.post(url, headers=app_head, data=body)
    return json.loads(r.text)["session_token"]

def get_cookie(session_token, userLang='en_US', ver='1.5.7'):
    '''Returns a new cookie provided the session_token.'''

    global version
    version = ver

    timestamp = int(time.time())
    guid = str(uuid.uuid4())

    app_head = {
        'Host':            'accounts.nintendo.com',
        'Accept-Encoding': 'gzip',
        'Content-Type':    'application/json; charset=utf-8',
        'Accept-Language': userLang,
        'Content-Length':  '439',
        'Accept':          'application/json',
        'Connection':      'Keep-Alive',
        'User-Agent':      'OnlineLounge/1.10.0 NASDKAPI Android'
    }

    body = {
        'client_id':     '71b963c1b7b6d119', # Splatoon 2 service
        'session_token': session_token,
        'grant_type':    'urn:ietf:params:oauth:grant-type:jwt-bearer-session-token'
    }

    url = "https://accounts.nintendo.com/connect/1.0.0/api/token"

    r = requests.post(url, headers=app_head, json=body)
    id_response = json.loads(r.text)

    # get user info
    try:
        app_head = {
            'User-Agent':      'OnlineLounge/1.10.0 NASDKAPI Android',
            'Accept-Language': userLang,
            'Accept':          'application/json',
            'Authorization':   'Bearer {}'.format(id_response["access_token"]),
            'Host':            'api.accounts.nintendo.com',
            'Connection':      'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }
    except:
        print("Not a valid authorization request. Please delete config.txt and try again.")
        print("Error from Nintendo (in api/token step):")
        print(json.dumps(id_response, indent=2))
        sys.exit(1)
    url = "https://api.accounts.nintendo.com/2.0.0/users/me"

    r = requests.get(url, headers=app_head)
    user_info = json.loads(r.text)

    nickname = user_info["nickname"]

    # get access token
    app_head = {
        'Host':             'api-lp1.znc.srv.nintendo.net',
        'Accept-Language':  userLang,
        'User-Agent':       'com.nintendo.znca/1.10.0 (Android/7.1.2)',
        'Accept':           'application/json',
        'X-ProductVersion': '1.10.0',
        'Content-Type':     'application/json; charset=utf-8',
        'Connection':       'Keep-Alive',
        'Authorization':    'Bearer',
        # 'Content-Length':   '1036',
        'X-Platform':       'Android',
        'Accept-Encoding':  'gzip'
    }

    body = {}
    try:
        idToken = id_response["access_token"]

        flapg_nso = call_flapg_api(idToken, guid, timestamp, "nso")

        parameter = {
            'f':          flapg_nso["f"],
            'naIdToken':  flapg_nso["p1"],
            'timestamp':  flapg_nso["p2"],
            'requestId':  flapg_nso["p3"],
            'naCountry':  user_info["country"],
            'naBirthday': user_info["birthday"],
            'language':   user_info["language"]
        }
    except SystemExit:
        sys.exit(1)
    except:
        print("Error(s) from Nintendo:")
        print(json.dumps(id_response, indent=2))
        print(json.dumps(user_info, indent=2))
        sys.exit(1)
    body["parameter"] = parameter

    url = "https://api-lp1.znc.srv.nintendo.net/v1/Account/Login"

    r = requests.post(url, headers=app_head, json=body)
    splatoon_token = json.loads(r.text)

    try:
        idToken = splatoon_token["result"]["webApiServerCredential"]["accessToken"]
        flapg_app = call_flapg_api(idToken, guid, timestamp, "app")
    except:
        print("Error from Nintendo (in Account/Login step):")
        print(json.dumps(splatoon_token, indent=2))
        sys.exit(1)

    # get splatoon access token
    try:
        app_head = {
            'Host':             'api-lp1.znc.srv.nintendo.net',
            'User-Agent':       'com.nintendo.znca/1.10.0 (Android/7.1.2)',
            'Accept':           'application/json',
            'X-ProductVersion': '1.10.0',
            'Content-Type':     'application/json; charset=utf-8',
            'Connection':       'Keep-Alive',
            'Authorization':    'Bearer {}'.format(splatoon_token["result"]["webApiServerCredential"]["accessToken"]),
            'Content-Length':   '37',
            'X-Platform':       'Android',
            'Accept-Encoding':  'gzip'
        }
    except:
        print("Error from Nintendo (in Account/Login step):")
        print(json.dumps(splatoon_token, indent=2))
        sys.exit(1)

    body = {}
    parameter = {
        'id':                5741031244955648,
        'f':                 flapg_app["f"],
        'registrationToken': flapg_app["p1"],
        'timestamp':         flapg_app["p2"],
        'requestId':         flapg_app["p3"]
    }
    body["parameter"] = parameter

    url = "https://api-lp1.znc.srv.nintendo.net/v2/Game/GetWebServiceToken"

    r = requests.post(url, headers=app_head, json=body)
    splatoon_access_token = json.loads(r.text)

    # get cookie
    try:
        app_head = {
            'Host':                    'app.splatoon2.nintendo.net',
            'X-IsAppAnalyticsOptedIn': 'false',
            'Accept':                  'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding':         'gzip,deflate',
            'X-GameWebToken':          splatoon_access_token["result"]["accessToken"],
            'Accept-Language':         userLang,
            'X-IsAnalyticsOptedIn':    'false',
            'Connection':              'keep-alive',
            'DNT':                     '0',
            'User-Agent':              'Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36',
            'X-Requested-With':        'com.nintendo.znca'
        }
    except:
        print("Error from Nintendo (in Game/GetWebServiceToken step):")
        print(json.dumps(splatoon_access_token, indent=2))
        sys.exit(1)

    url = "https://app.splatoon2.nintendo.net/?lang={}".format(userLang)
    r = requests.get(url, headers=app_head)
    return nickname, r.cookies["iksm_session"]

def get_hash_from_s2s_api(id_token, timestamp):
    '''Passes an id_token and timestamp to the s2s API and fetches the resultant hash from the response.'''

    # check to make sure we're allowed to contact the API. stop spamming my web server pls
    # config_file = open(config_path, "r")
    # config_data = json.load(config_file)
    # config_file.close()
    # try:
    #     num_errors = config_data["api_errors"]
    # except:
    #     num_errors = 0

    # if num_errors >= 5:
    #     print("Too many errors received from the splatnet2statink API. Further requests have been blocked until the \"api_errors\" line is manually removed from config.txt. If this issue persists, please contact @frozenpandaman on Twitter/GitHub for assistance.")
    #     sys.exit(1)

    # proceed normally
    try:
        api_app_head = { 'User-Agent': "splatnet2statink/{}".format(version) }
        api_body = { 'naIdToken': id_token, 'timestamp': timestamp }
        api_response = requests.post("https://elifessler.com/s2s/api/gen2", headers=api_app_head, data=api_body)
        return json.loads(api_response.text)["hash"]
    except:
        print("Error from the splatnet2statink API:\n{}".format(json.dumps(json.loads(api_response.text), indent=2)))

        # add 1 to api_errors in config
        config_file = open(config_path, "r")
        config_data = json.load(config_file)
        config_file.close()
        try:
            num_errors = config_data["api_errors"]
        except:
            num_errors = 0
        num_errors += 1
        config_data["api_errors"] = num_errors

        config_file = open(config_path, "w") # from write_config()
        config_file.seek(0)
        config_file.write(json.dumps(config_data, indent=4, sort_keys=True, separators=(',', ': ')))
        config_file.close()

        sys.exit(1)

def call_flapg_api(id_token, guid, timestamp, type):
    '''Passes in headers to the flapg API (Android emulator) and fetches the response.'''

    try:
        api_app_head = {
            'x-token': id_token,
            'x-time':  str(timestamp),
            'x-guid':  guid,
            'x-hash':  get_hash_from_s2s_api(id_token, timestamp),
            'x-ver':   '3',
            'x-iid':   type
        }
        api_response = requests.get("https://flapg.com/ika2/api/login?public", headers=api_app_head)
        f = json.loads(api_response.text)["result"]
        return f
    except:
        try: # if api_response never gets set
            if api_response.text:
                print(u"Error from the flapg API:\n{}".format(json.dumps(json.loads(api_response.text), indent=2, ensure_ascii=False)))
            elif api_response.status_code == requests.codes.not_found:
                print("Error from the flapg API: Error 404 (offline or incorrect headers).")
            else:
                print("Error from the flapg API: Error {}.".format(api_response.status_code))
        except:
            pass
        sys.exit(1)

def enter_cookie():
    '''Prompts the user to enter their iksm_session cookie'''

    new_cookie = input("Go to the page below to find instructions to obtain your iksm_session cookie:\nhttps://github.com/frozenpandaman/splatnet2statink/wiki/mitmproxy-instructions\nEnter it here: ")
    while len(new_cookie) != 40:
        new_cookie = input("Cookie is invalid. Please enter it again.\nCookie: ")
    return new_cookie

if __name__ == '__main__':
    # for dev purposes
    print(get_user('does not exist'))
    print(get_user('580157651548241940'))
    exit()
    with open('data/users/nintendo_keys.json') as file_:
        user_keys = json.loads(file_.read())

    user = user_keys[discord_id]
    cookie = get_cookie(user['session_token'])
    print(cookie)
