import json

import requests

BASE_PATH = 'https://firestore.googleapis.com/v1'

with open('private/keys.json') as file_:
    data = json.loads(file_.read())
    private_key = data['service_account']['private_key'].splitlines()[1:-1]
    GKEY = data['firebase']
    PID = data['project_id']
    OAUTH = data['oauth']


def make_fields(data):
    return {key: {'stringValue': value} for key, value in data.items()}


def list_documents(collection):
    path = f'projects/{PID}/databases/(default)/documents/{collection}'
    url = f'{BASE_PATH}/{path}?key={GKEY}'
    req = requests.get(url)
    return req.json()


def create_document(collection, document, fields):
    path = f'projects/{PID}/databases/(default)/documents/{collection}'
    url = f'{BASE_PATH}/{path}?key={GKEY}&documentId={document}'

    data = {
        'fields': fields
    }

    req = requests.post(url, json=data)

    return req.json()


def update_document(collection, document, fields):
    path = f'projects/{PID}/databases/(default)/documents/{collection}/{document}'
    update_mask = '&'.join([f'updateMask.fieldPaths={x}' for x in fields.keys()])
    url = f'{BASE_PATH}/{path}?key={GKEY}&{update_mask}'

    data = {
        'fields': fields
    }

    req = requests.patch(url, json=data)

    return req.json()


def get_document(collection, document):
    path = f'projects/{PID}/databases/(default)/documents/{collection}/{document}'
    url = f'{BASE_PATH}/{path}?key={GKEY}'

    req = requests.get(url)
    return req.json()


def add_user_cookies(aid, data):
    fields = {key: {'stringValue': value} for key, value in data.items()}
    document = create_document('users', str(aid), fields)
    return document


class OAuth:
    client_id = OAUTH['client_id']
    client_secret = OAUTH['client_secret']

    def get_code_url(self, scope, redirect_uri):
        auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?'
        auth_url += 'scope=' + scope + '&'
        auth_url += 'access_type=offline&'
        auth_url += 'redirect_uri=' + redirect_uri + '&'
        auth_url += 'response_type=code&'
        auth_url += 'client_id=' + self.client_id

        return auth_url

    def send_tokens_request(self, code, redirect_uri):
        url = 'https://oauth2.googleapis.com/token?'

        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }

        return requests.post(url, data=data)


    def get_tokens(self, scope='https://www.googleapis.com/auth/datastore', redirect_uri='http://localhost:5000'):
        code = input(f'{self.get_code_url(scope, redirect_uri)}\nCode:')
        return self.send_tokens_request(code, redirect_uri)


if __name__ == '__main__':
    # with open('data/users/nintendo_keys.json') as f:
    #     data = json.loads(f.read())

    # for aid, data in data.items():
    #     add_user_cookies(aid, data)print(update_document('users', '580157651548241940', make_fields({'wow': 'sick'})))
    # print(update_document('users', '580157651548241940', make_fields({'success': 'i think so'})))
    pass

