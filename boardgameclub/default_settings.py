import pkg_resources


class Config(object):
    DEBUG = False
    DB_URL = 'sqlite:///' + pkg_resources.resource_filename(
        'boardgameclub', 'data/bgclub.db')
    APP_URL = 'http://localhost:5000'


class DevelopmentConfig(Config):
    DEBUG = True
