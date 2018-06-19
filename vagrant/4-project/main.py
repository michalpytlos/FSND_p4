from flask import Flask, render_template, url_for, request, redirect, session, abort
from database import db_session
from models import Club, ClubGame, Game, Post,  User, UserGame, GameCategory
import requests
from xml.etree import ElementTree
import sqlalchemy
from oauth2client import client
import time

app = Flask(__name__)

CLIENT_SECRET_FILE = 'client_secret.json'
CLIENT_ID = json.loads(open('client_secret.json', 'r').read())['web']['client_id']


# Remove database session at the end of each request
@app.teardown_appcontext
def remove_session(exception=None):
    db_session.remove()


def validate_id_token(token, token_jwt):
    # validate id_token as per https://developers.google.com/identity/protocols/OpenIDConnect
    url = 'https://www.googleapis.com/oauth2/v3/tokeninfo'
    params = 'id_token={}'.format(token_jwt)
    r = requests.get(url, params=params)

    if (
        r.status_code == 200 and r.json()['aud'] == token['aud'] and  # is the token properly signed by the issuer?
        token['iss'] in ('https://accounts.google.com', 'accounts.google.com') and  # was it issued by google?
        token['aud'] == CLIENT_ID and  # is it intended for this app?
        token['exp'] > int(time.time())  # is it still valid (not expired)?
    ):
        return True


def bgg_game_options(bg_name):
    # Search for games on bgg API by name
    # Return list of dictionaries. Each dictionary holds basic info about a game.
    bgg_games = []
    url = 'https://boardgamegeek.com/xmlapi2/search'
    payload = {'query': bg_name, 'type': 'boardgame'}
    r = requests.get(url, params=payload)
    print r.url
    print r.content
    # Parse the xml response
    root = ElementTree.fromstring(r.content)
    for item in root.findall('item'):
        bgg_id = item.get('id')
        game_name = item.find('name').get('value')
        try:
            year = item.find('yearpublished').get('value')
        except AttributeError:
            year = ''
        bgg_games.append({'id': bgg_id, 'name': game_name, 'year': year})
    return bgg_games


def bgg_game_info(bgg_id):
    # Get game info from bgg API
    # Return dictionary with all the required game info
    game_info = {'bgg_id': bgg_id}
    url = 'https://www.boardgamegeek.com/xmlapi2/thing'
    payload = {'id': bgg_id, 'stats': 1}
    r = requests.get(url, params=payload)
    # Parse the xml response
    root = ElementTree.fromstring(r.content)[0]
    # name
    for name in root.findall('name'):
        if name.get('type') == 'primary':
            game_info['name'] = name.get('value')
    # image
    game_info['image'] = root.find('image').text
    # categories (max 3)
    categories = []
    for link in root.findall('link'):
        if link.get('type') == 'boardgamecategory':
            categories.append(link.get('value'))
    for i in range(3):
        try:
            category_name = categories[i]
            category = check_game_category(category_name)
        except IndexError:
            category = ''
        game_info['category_{}'.format(i+1)] = category
    # complexity/weight
    game_info['weight'] = root.find('statistics').find('ratings').find('averageweight').get('value')
    # bgg_rating
    game_info['bgg_rating'] = root.find('statistics').find('ratings').find('average').get('value')
    # other properties
    properties = ['year_published', 'min_age', 'min_playtime', 'max_playtime', 'min_players', 'max_players']
    for property in properties:
        game_info[property] = root.find(property.replace('_', '')).get('value')

    game_info['bgg_link'] = 'https://boardgamegeek.com/boardgame/{}/{}'.format(bgg_id, game_info['name'])
    return game_info


def check_game_category(category_name):
    # Check if a given game category is already in the database.
    # If not, add to the database
    # Return the category id
    category = GameCategory.query.filter_by(name=category_name).scalar()
    if not category:
        new_category = GameCategory(name=category_name)
        db_session.add(new_category)
        db_session.commit()
        category = GameCategory.query.filter_by(name=category_name).scalar()
    return category.id


def check_game(bgg_id):
    # Check if a given game is already in the database.
    # If not, get the game info from bgg API and add the game to the database
    # Return the game id
    bgame = Game.query.filter_by(bgg_id=bgg_id).scalar()
    if not bgame:
        bgg_game = bgg_game_info(bgg_id)
        bgame = Game(**bgg_game)
        db_session.add(bgame)
        db_session.commit()
        print 'Game added to the database!'
    else:
        print 'Game already in the database'
    return bgame.id


def get_game(game_id):
    return Game.query.filter_by(id=game_id).scalar()


def category_dict(bgames):
    # return dictionary where each key is a game id and the corresponding value is a list of categories, given by name,
    # to which this game belongs
    categories = {}
    for bgame in bgames:
        categories[str(bgame.id)] = get_categories(bgame)
    return categories


def get_categories(bgame):
    # return list of all category names for a given game
    category_ids = []
    category_names = []
    for i in range(1, 4):
        category = getattr(bgame, 'category_{}'.format(i))
        if category:
            category_ids.append(category)
    for id in category_ids:
        category = GameCategory.query.filter_by(id=id).scalar()
        category_names.append(category.name)
    return category_names


def game_search_query_builder(key, value):
    # return textual sql query for one argument of a game search request
    # the returned query typically is just a part of a much longer query thus the 'AND' operator in the returned string
    if len(value) == 0 or value == 'any':
        return ''
    d = {'name': "name LIKE '{value}%'",
         'category': "(category_1='{value}' OR category_2='{value}' OR category_3='{value}')",
         'rating-min': 'bgg_rating>={value}',
         'players-from': 'min_players<={value}',
         'players-to': 'max_players>={value}',
         'time-from': 'max_playtime>={value}',
         'time-to': 'min_playtime<={value}',
         'weight-min': 'weight>={value}',
         'weight-max': 'weight<={value}',
         }
    return d[key].format(value=value) + ' AND '


# dummy database objects
user_1 = {
    'name': 'John Smith',
    'email': '12345@gmail.com',
    'games': {'Dominion': 8, 'Stone Age': 7},  # value is user rating
    'image': 'https://upload.wikimedia.org/wikipedia/commons/2/25/Benjamin_Franklin_by_Joseph_Duplessis_1778.jpg',
    'about': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut '
             'labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris '
             'nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit '
             'esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in '
             'culpa qui officia deserunt mollit anim id est laborum.'

}

game_club = {
    'members': ['user_1'],
    'games': ['Dominion', 'Stone Age'],
    'about': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut '
             'labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris '
             'nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit '
             'esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in '
             'culpa qui officia deserunt mollit anim id est laborum.'
}

post_1 = {
    'title': 'Hello',
    'author': 'John Smith',
    'date': '06/06/2018',
    'body': 'I like board games!'
}

post_2 = {
    'title': 'Card games',
    'author': 'John Smith',
    'date': '07/06/2018',
    'body': 'And card games too!'
}


@app.route('/')
def home():
    return render_template('club.html', club=game_club, posts=[post_1, post_2], members=[user_1], games=[])


@app.route('/signin')
def sign_in():
    if 'username' in session:
        redirect('/')
    return render_template('sign-in.html')


@app.route('/gconnect', methods=['POST'])
def g_connect():
    # additional csrf check
    if not request.headers.get('X-Requested-With'):
        abort(403)
    # get one-time code from the end-user
    auth_code = request.data
    # exchange one-time code for id_token and access_token
    try:
        credentials = client.credentials_from_clientsecrets_and_code(
            CLIENT_SECRET_FILE,
            ['https://www.googleapis.com/auth/drive.appdata', 'profile', 'email'],
            auth_code)
    except client.FlowExchangeError:
        print 'Failed to upgrade one-time authorization code.'
        abort(401)
    # validate id_token
    if not validate_id_token(credentials.id_token, credentials.id_token_jwt):
        print 'id token is not valid'
        abort(500)
    # get user info from access token
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    user_data = answer.json()
    # store user info in the session for later use
    session['email'] = credentials.id_token['email']
    session['username'] = user_data['name']
    session['access_token'] = credentials.access_token
    return user_data['name']


@app.route('/gdisconnect')
def g_disconnect():
    print session
    # check if user is connected
    if 'access_token' not in session:
        print 'Access token missing'
        abort(401)
    # revoke access token
    r = requests.post('https://accounts.google.com/o/oauth2/revoke',
                      params={'token': session['access_token']},
                      headers={'content-type': 'application/x-www-form-urlencoded'})
    # delete user info from session
    if r.status_code == 200:
        del session['email']
        del session['username']
        del session['access_token']
        print session
        return 'Successfully disconnected'
    else:
        print 'Failed to revoke access token'
        print r.text
        abort(500)


@app.route('/users/new')
def new_user():
    return render_template('user-create.html', user=user_1)


@app.route('/users/<int:user_id>')
def profile(user_id):
    return render_template('user.html', user=user_1, games=[])


@app.route('/users/<int:user_id>/edit')
def edit_user(user_id):
    return 'edit user profile'


@app.route('/users/<int:user_id>/delete')
def delete_user(user_id):
    return 'delete user profile'


@app.route('/games/new', methods=['GET', 'POST'])
def new_game():
    if request.method == 'GET':
        # Show the game options matching the specified name
        bgg_options = bgg_game_options(request.args.get('name'))
        return render_template('game-options.html', games=bgg_options)
    else:
        # Add the chosen game to the database
        game_id = check_game(request.form['bgg-id'])
        return redirect(url_for('game', game_id=game_id))


@app.route('/games/<int:game_id>')
def game(game_id):
    bgame = get_game(game_id)
    categories = get_categories(bgame)
    return render_template('game.html', game=bgame, game_id=game_id, categories=categories)


@app.route('/games/<int:game_id>/edit')
def edit_game(game_id):
    # Update game info from bgg API
    bgame = get_game(game_id)
    game_info = bgg_game_info(bgame.bgg_id)
    for key, value in game_info.iteritems():
        setattr(bgame, key, value)
    db_session.commit()
    return redirect(url_for('game', game_id=game_id))


@app.route('/games/<int:game_id>/delete')
def delete_game(game_id):
    bgame = get_game(game_id)
    db_session.delete(bgame)
    db_session.commit()
    return redirect(url_for('home'))


@app.route('/games/search')
def game_finder():
    all_categories = GameCategory.query.all()
    games = []
    categories = {}
    if len(request.args) > 0:
        query = ''
        for key, value in request.args.iteritems():
            query += game_search_query_builder(key, value)
        query = query[:-5]
        print query
        games = Game.query.filter(sqlalchemy.text(query)).all()
        categories = category_dict(games)
    return render_template('game-finder.html', games=games, all_categories=all_categories, categories=categories)


if __name__ == '__main__':
    app.secret_key = '\xa7B\xf8w\x13\xcb\x12\x07\xd5\x95_C\x91\xd5\x8c\xf6\\\xb3\xb7\x16\x0b\xab+\x94'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)