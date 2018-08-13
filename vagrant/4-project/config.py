import json

DEBUG = True
SECRET_KEY = ('\xa7B\xf8w\x13\xcb\x12\x07\xd5\x95_C\x91\xd5\x8c\xf6\\\xb3\xb7'
              '\x16\x0b\xab+\x94')
CLIENT_SECRET_FILE = 'client_secret.json'
CLIENT_ID = json.loads(
    open('client_secret.json', 'r').read())['web']['client_id']

