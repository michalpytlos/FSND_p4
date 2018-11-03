import pkg_resources


class Config(object):
    DEBUG = False
    SECRET_KEY = ('\xa7B\xf8w\x13\xcb\x12\x07\xd5\x95_C\x91\xd5\x8c\xf6\\\xb3'
                  '\xb7\x16\x0b\xab+\x94')
    DB_URL = 'sqlite:///' + pkg_resources.resource_filename(
        'boardgameclub', 'data/bgclub.db')


class DevelopmentConfig(Config):
    DEBUG = True
