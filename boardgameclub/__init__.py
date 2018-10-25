from flask import Flask

app = Flask(__name__)

# Configure the app
app.config.from_object('config')

# Jinja2 globals
app.jinja_env.globals['client_id'] = app.config['CLIENT_ID']

import boardgameclub.views
