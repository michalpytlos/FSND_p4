from flask import Flask
import os
import json


app = Flask(__name__, instance_relative_config=True)

# Configure the app
app.config.from_object('boardgameclub.default_settings.Config')
app.config.from_pyfile('config.py', silent=True)
app.config['CLIENT_SECRET_FILE'] = os.path.join(
    app.instance_path, 'client_secret.json')
app.config['CLIENT_ID'] = json.loads(
    open(app.config['CLIENT_SECRET_FILE'], 'r').read())['web']['client_id']

# Jinja2 globals
app.jinja_env.globals['client_id'] = app.config['CLIENT_ID']
app.jinja_env.globals['app_url'] = app.config['APP_URL']

import boardgameclub.views
