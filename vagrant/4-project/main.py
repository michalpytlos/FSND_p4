#!/usr/bin/env python2.7
from flask import Flask, render_template, url_for, request, redirect, session, abort, make_response, jsonify
from database import db_session
from models import Club, Game, Post,  User, GameCategory, ClubAdmin, clubs_games_assoc, users_games_assoc
import requests
from xml.etree import ElementTree
import sqlalchemy
from oauth2client import client
import json
import time
import string
import random
from decimal import Decimal
import sqlalchemy.orm.exc


app = Flask(__name__)

CLIENT_SECRET_FILE = 'client_secret.json'
CLIENT_ID = json.loads(open('client_secret.json', 'r').read())['web']['client_id']


@app.before_request
def csrf_protect():
    """Abort create, update and delete requests without correct csrf tokens.

    Csrf protection as per:
    'http://flask.pocoo.org/snippets/3/' posted by Dan Jacob on 2010-05-03 @ 11:29 and filed in Security
    but with only one token per session.
    """
    if request.method in ('POST', 'PATCH', 'DELETE'):
        print 'validating csrf token'
        token = session.get('_csrf_token')
        if not token or token not in (request.form.get('_csrf_token'),
                                      request.get_json().get('_csrf_token') if request.get_json() else None):
            print 'failed csrf token test'
            abort(403)
        else:
            print 'csrf token ok'


def generate_csrf_token():
    """Add csrf token to the session and return the csrf token."""
    if '_csrf_token' not in session:
        print 'generating csrf token'
        session['_csrf_token'] = random_string()
    return session['_csrf_token']


app.jinja_env.globals['csrf_token'] = generate_csrf_token


def random_string():
    """Create a random string."""
    chars = string.ascii_letters + string.digits
    return ''.join([chars[random.randint(0, 61)] for i in range(20)])


@app.teardown_appcontext
def remove_session(exception=None):
    """Remove database session at the end of each request."""
    db_session.remove()


@app.before_request
def ownership_required():
    """Prevent access to update and delete endpoints by non-authorized users."""
    if request.endpoint in ('profile_game_add', 'club_game_add') or request.method in ('PATCH', 'DELETE'):
        print 'checking ownership'
        if 'user_id' not in session or not check_ownership():
            abort(403)
        else:
            print 'ownership ok'


def check_ownership():
    """Verify if the user is the owner of the requested resource."""
    user_id = session.get('user_id')
    if not user_id:
        return False
    elif 'club_' in request.endpoint or 'home' in request.endpoint:
        return True if ClubAdmin.query.filter_by(user_id=user_id).scalar() else False
    elif 'profile_' in request.endpoint:
        return request.view_args['user_id'] == user_id
    elif request.endpoint == 'post_':
        return True if Post.query.filter_by(id=request.view_args['post_id'], user_id=user_id).scalar() else False
    else:
        print 'Unable to verify ownership'
        return False


@app.before_request
def login_required():
    """Prevent access to create endpoints by non-authenticated users."""
    if (
        (request.endpoint in ('post_add', 'profile_add', 'g_disconnect') or
         request.endpoint == 'game_' and request.method == 'POST') and
        'username' not in session
    ):
        abort(401)


def validate_id_token(token, token_jwt):
    """Validate id_token as per 'https://developers.google.com/identity/protocols/OpenIDConnect'."""
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


def json_response(body, code):
    """Build a JSON response."""
    j_response = make_response(json.dumps(body), code)
    j_response.headers['Content-Type'] = 'application/json'
    return j_response


def error_response(err_msg, code):
    """Build a one-line JSON error response."""
    err_response = make_response(json.dumps({"error-msg": err_msg}), code)
    err_response.headers['Content-Type'] = 'application/json'
    return err_response


def bgg_game_options(bg_name):
    """Search for games on bgg API by name and return all the matching options.

    Args:
        bg_name (str): game name.

    Returns:
        List of dictionaries. Each dictionary holds basic info about a game.
    """
    bgg_games = []
    url = 'https://boardgamegeek.com/xmlapi2/search'
    payload = {'query': bg_name, 'type': 'boardgame'}
    r = requests.get(url, params=payload)
    print r.url
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
    """Get game info from bgg API; return dictionary with game info and list of game category objects ."""
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
    # complexity/weight
    game_info['weight'] = root.find('statistics').find('ratings').find('averageweight').get('value')
    # bgg_rating
    game_info['bgg_rating'] = root.find('statistics').find('ratings').find('average').get('value')
    # other properties
    properties = ['year_published', 'min_age', 'min_playtime', 'max_playtime', 'min_players', 'max_players']
    for property in properties:
        game_info[property] = root.find(property.replace('_', '')).get('value')

    game_info['bgg_link'] = 'https://boardgamegeek.com/boardgame/{}/{}'.format(bgg_id, game_info['name'])
    # categories
    categories = []
    for link in root.findall('link'):
        if link.get('type') == 'boardgamecategory':
            categories.append(check_game_category(link.get('value')))
    return game_info, categories


def check_user(email, name, picture):
    """Check if the user is already in the database; if not, make a new entry. Return user's id."""
    user = User.query.filter_by(email=email).scalar()
    new_user = False
    if not user:
        print 'adding new user to the db'
        user = User(email=email, name=name, picture=picture)
        db_session.add(user)
        db_session.commit()
        user = User.query.filter_by(email=email).scalar()
        new_user = True
    else:
        print 'user already exists'
    return user.id, new_user


def check_game_category(category_name):
    """Check if the game category is already in the database; if not, make a new entry. Return the category."""
    category = GameCategory.query.filter_by(name=category_name).scalar()
    if not category:
        new_category = GameCategory(name=category_name)
        db_session.add(new_category)
        db_session.commit()
        category = GameCategory.query.filter_by(name=category_name).scalar()
    return category


def check_game(bgg_id):
    """Check if the game is already in the database; if not, make a new entry. Return the game."""
    bgame = Game.query.filter_by(bgg_id=bgg_id).scalar()
    if not bgame:
        # get the game info from bgg API
        game_info, bgg_categories = bgg_game_info(bgg_id)
        # add the game to the database
        bgame = Game(**game_info)
        bgame.categories = bgg_categories
        db_session.add(bgame)
        db_session.commit()
        print 'Game added to the database!'
    else:
        print 'Game already in the database'
    return bgame


def make_posts_read(posts):
    """Prepare data on a set of posts for the template engine.

    Args:
        posts (list): list of Post objects.

    Returns:
         List of dictionaries. Each dictionary holds all the post data required by the template engine.
    """
    posts_read = []
    user_id = session.get('user_id')
    for post in posts:
        user = post.author
        post_dict = {
            'id': post.id,
            'subject': post.subject,
            'body': post.body,
            'author': user.name,
            'author_picture': user.picture,
            'posted': time.strftime("%d/%m/%Y, %H:%M", time.gmtime(post.posted)),
            'owner': post.user_id == user_id
        }
        if post.edited:
            post_dict['edited'] = time.strftime("%d/%m/%Y, %H:%M", time.gmtime(post.edited))
        posts_read.append(post_dict)
    return posts_read


def game_query_builder(key, value, query):
    """Modify textual sql query in order take into account an additional WHERE condition.

    Args:
        key (str): condition name.
        value (str): condition value.
        query (str): SQL query.

    Returns:
        str: modified SQL query.
    """
    d = {'id': "id in ({value})",
         'name': "name LIKE '{value}%'",
         'rating-min': 'bgg_rating>={value}',
         'players-from': 'min_players<={value}',
         'players-to': 'max_players>={value}',
         'time-from': 'max_playtime>={value}',
         'time-to': 'min_playtime<={value}',
         'weight-min': 'weight>={value}',
         'weight-max': 'weight<={value}',
         }
    if len(value) == 0 or value == 'any' or not d.get(key):
        # do nothing
        return query
    elif key == 'id' and 'id in' in query:
        pos = query.find(')', query.find('id in'))
        return query[:pos] + ', ' + value + query[pos:]
    else:
        return query + d[key].format(value=value) + ' AND '


def clear_games(*games):
    """Remove orphaned games from the database.

    If any of the games is not owned by any user or the club, remove it from the database.
    """
    for game in games:
        if len(game.users) == 0 and len(game.clubs) == 0:
            categories = game.categories
            db_session.delete(game)
            db_session.commit()
            clear_categories(*categories)


def clear_categories(*categories):
    """Remove orphaned game categories from the database"""
    for category in categories:
        if len(category.games) == 0:
            db_session.delete(category)
            db_session.commit()


def patch_resource(attributes, my_obj):
    """Patch database resource.

    Args:
        attributes (list): list of dictionaries; each dict is in the following format:
        {'name': attr_name, 'value': attr_value}.
        my_obj: instance of any of the models classes.
    """
    for attribute in attributes:
        setattr(my_obj, attribute['name'], attribute['value'])
    db_session.add(my_obj)
    db_session.commit()


def validate_api_game_query(query_dict):
    """Validate keys and values of the query.

    Args:
        query_dict (dict): dictionary where each key:value pair represents condition-name:condition-value pair of an SQL
        WHERE condition.

    Returns:
        bool: True if all keys and values are valid, False otherwise.
    """
    args_int = ['club', 'user', 'id', 'category', 'rating-min', 'players-from', 'players-to', 'time-from', 'time-to',
                'weight-min', 'weight-max']
    args_other = ['name']
    args_dupl = ['user', 'id', 'category']
    for key, value in query_dict.iteritems(multi=True):
        if(
            key not in args_int + args_other or  # check if any of the keys is invalid
            key in args_int and not value.isdigit()  # check if any of the values is invalid
        ):
            return False
    # check if there are any non-allowed key duplicates
    for key, values in query_dict.iterlists():
        if key not in args_dupl and len(values) > 1:
            return False
    # confirm that players-to >= players-from and that either both or none of these two keys are present
    if (
        'players-from' in query_dict and query_dict.get('players-to', -1, type=int) < int(query_dict['players-from']) or
        'players-to' in query_dict and 'players-from' not in query_dict
    ):
        return False
    return True


def dicts_purge(p_dicts, *keep_keys):
    """Purge dictionaries of unwanted key:value pairs.

    Args:
        p_dicts (list): list of dicts to be purged.
        *keep_keys: list of keys to be kept.

    Returns:
        List of purged dicts.
    """
    for p_dict in p_dicts:
        for key in p_dict.keys():
            if key not in keep_keys:
                del p_dict[key]
    return p_dicts


def sql_to_dicts(*games):
    """Convert Game objects to dictionaries.

    Each column-name:value pair in an object is converted to a key:value pair in the corresponding dictionary.

    Args:
        *games: list of Game objects.

    Returns:
        list of dictionaries.
    """
    sql_dicts = []
    for game in games:
        keys = game.__table__.columns.keys()
        values = [getattr(game, key) for key in keys]
        values = [float(value) if type(value) == Decimal else value for value in values]
        sql_dicts.append(dict(zip(keys, values)))
    return sql_dicts


def sign_out():
    """Sign out a user."""
    try:
        # revoke access token if possible
        r = requests.post('https://accounts.google.com/o/oauth2/revoke',
                          params={'token': session['access_token']},
                          headers={'content-type': 'application/x-www-form-urlencoded'})
        if r.status_code != 200:
            print 'Failed to revoke access token'
            print r.text
        # delete user info from session
        del session['email']
        del session['username']
        del session['access_token']
        del session['user_id']
        del session['_csrf_token']
        print 'Signed out'
    except KeyError:
        print 'Not signed in'
        abort(401)


def init_club_info():
    """Add Board Game Club to the database.

    Function used only when creating a new database. Call this function directly from a Python interpreter.
    """
    club = Club(name='Board Game Club')
    db_session.add(club)
    db_session.commit()


def add_club_admin(email):
    """Add user to club admins.

    Function used by the external program add_admin.
    """
    user = User.query.filter_by(email=email).scalar()
    if user:
        admin = ClubAdmin(user_id=user.id)
        db_session.add(admin)
        db_session.commit()
        print 'User added to club admins'
    else:
        print 'User not found'


'''*****************************************    HANDLERS BELOW     **************************************************'''


@app.route('/')
def home():
    """Return the app's main page."""
    club = Club.query.filter_by(id=1).scalar()
    members = User.query.all()
    posts = Post.query.all()
    posts_read = make_posts_read(posts)
    return render_template('club.html', club=club, posts=posts_read, members=members,
                           games=club.games,
                           owner=check_ownership())


@app.route('/club', methods=['PATCH'])
def club_():
    """Update the Club."""
    club = Club.query.filter_by(id=1).scalar()
    attributes = request.get_json()['data']['attributes']
    patch_resource(attributes, club)
    return '', 204


@app.route('/club/games/add', methods=['GET', 'POST'])
def club_game_add():
    """Create ClubGame or return page with form to do so.

    Use POST and GET methods respectively.
    """
    if request.method == 'GET':
        # Show the game options matching the specified name
        bgg_options = bgg_game_options(request.args['name'])
        return render_template('game-options.html', games=bgg_options)
    else:
        # Add the chosen game to the database
        game = check_game(request.form['bgg-id'])
        club = Club.query.filter_by(id=1).scalar()
        club.games.append(game)
        db_session.add(club)
        db_session.commit()
        return redirect(url_for('home'))


@app.route('/club/games/<int:game_id>', methods=['DELETE'])
def club_game_(game_id):
    """Delete ClubGame."""
    club = Club.query.filter_by(id=1).scalar()
    try:
        game = Game.query.filter_by(id=game_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        abort(404)
    club.games.remove(game)
    db_session.commit()
    clear_games(game)
    return '', 204


@app.route('/posts/add', methods=['GET', 'POST'])
def post_add():
    """Create Post or return page with form to do so.

    Use POST and GET methods respectively.
    """
    if request.method == 'GET':
        return render_template('post-new.html')
    else:
        # Add Post to the database
        post_data = {
            'user_id': session['user_id'],
            'subject': request.form['subject'],
            'body': request.form['body'],
            'posted': int(time.time())
        }
        post = Post(**post_data)
        db_session.add(post)
        db_session.commit()
        return redirect(url_for('home'))


@app.route('/posts/<int:post_id>', methods=['PATCH', 'DELETE'])
def post_(post_id):
    """Update or Delete Post.

    Use PATCH and DELETE methods respectively.
    """
    post = Post.query.filter_by(id=post_id).scalar()
    if request.method == 'PATCH':
        # Update Post
        attributes = request.get_json()['data']['attributes']
        attributes.append({'name': 'edited', 'value': int(time.time())})
        patch_resource(attributes, post)
        return '', 204
    else:
        # Delete Post
        db_session.delete(post)
        db_session.commit()
        return '', 204


@app.route('/gconnect', methods=['POST'])
def g_connect():
    """Sign in user."""
    # additional csrf check
    if not request.headers.get('X-Requested-With'):
        abort(403)
    # get one-time code from the end-user
    auth_code = request.get_json().get('auth_code')
    # exchange one-time code for id_token and access_token
    try:
        credentials = client.credentials_from_clientsecrets_and_code(
            CLIENT_SECRET_FILE,
            ['https://www.googleapis.com/auth/drive.appdata', 'profile', 'email'],
            auth_code)
    except client.FlowExchangeError:
        return error_response('Failed to upgrade one-time authorization code.', 401)
    # validate id_token
    if not validate_id_token(credentials.id_token, credentials.id_token_jwt):
        return error_response('id token is not valid', 500)
    # get user info from access token
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    user_data = answer.json()
    # store user info in the session for later use
    session['email'] = credentials.id_token['email']
    session['username'] = user_data['name']
    session['access_token'] = credentials.access_token
    # If the user does not exist, add him to the database
    session['user_id'], new_user = check_user(session['email'], session['username'],  user_data['picture'])
    body = {'username': user_data['name'], 'user_id': session['user_id'], 'new_user': new_user}
    return json_response(body, 200)


@app.route('/gdisconnect', methods=['POST'])
def g_disconnect():
    """Sign out user."""
    sign_out()
    return '', 204


@app.route('/users/<int:user_id>/new')
def profile_add(user_id):
    """Return page with form letting the user update his/her new profile."""
    try:
        user = User.query.filter_by(id=user_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        abort(404)
    return render_template('profile-new.html', user=user)


@app.route('/users/<int:user_id>', methods=['GET', 'PATCH', 'DELETE'])
def profile_(user_id):
    """Return user's profile page or Update Profile or Delete Profile.

    Use GET, PATCH and DELETE methods respectively.
    """
    try:
        user = User.query.filter_by(id=user_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        abort(404)  # can be raised only on GET request; PATCH and DELETE are protected by check_ownership()
    if request.method == 'GET':
        # Return user's profile page
        return render_template('profile.html', user=user, games=user.games,
                               owner=check_ownership())
    elif request.method == 'PATCH':
        # Update Profile
        attributes = request.get_json()['data']['attributes']
        patch_resource(attributes, user)
        return '', 204
    else:
        # Delete Profile
        games = user.games
        db_session.delete(user)
        db_session.commit()
        clear_games(*games)
        sign_out()  # remove the user from session
        return '', 204


@app.route('/users/<int:user_id>/games/add', methods=['GET', 'POST'])
def profile_game_add(user_id):
    """Create UserGame or return page with form to do so.

    Use POST and GET methods respectively.
    """
    if request.method == 'GET':
        # Show the game options matching the specified name
        bgg_options = bgg_game_options(request.args['name'])
        return render_template('game-options.html', games=bgg_options)
    else:
        # Add the chosen game to the database
        game = check_game(request.form['bgg-id'])
        user = User.query.filter_by(id=user_id).scalar()
        user.games.append(game)
        db_session.add(user)
        db_session.commit()
        return redirect(url_for('profile_', user_id=user_id))


@app.route('/users/<int:user_id>/games/<int:game_id>', methods=['DELETE'])
def profile_game_(user_id, game_id):
    """Delete UserGame."""
    try:
        user = User.query.filter_by(id=user_id).one()
        game = Game.query.filter_by(id=game_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        abort(404)
    user.games.remove(game)
    db_session.commit()
    clear_games(game)
    return '', 204


@app.route('/games/<int:game_id>', methods=['GET', 'POST'])
def game_(game_id):
    """Return game page or Update Game.

    Use GET and POST methods respectively.
    """
    try:
        bgame = Game.query.filter_by(id=game_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        abort(404)
    if request.method == 'GET':
        # Return game page
        return render_template('game.html', game=bgame)
    else:
        # Update game info from bgg API
        game_info, bgg_categories = bgg_game_info(bgame.bgg_id)
        for key, value in game_info.iteritems():
            setattr(bgame, key, value)
        bgame.categories = bgg_categories
        db_session.commit()
        return redirect(url_for('game_', game_id=game_id))


@app.route('/games/search')
def game_finder():
    """Return game-finder page."""
    all_categories = GameCategory.query.all()
    games = []
    if len(request.args) > 0:
        # build SQL query
        query = ''
        for key, value in request.args.iteritems():
            query = game_query_builder(key, value, query)
        query = query[:-5]
        print query
        # get games satisfying the search criteria
        game_category = int(request.args['category'])
        if game_category == 0:
            games = Game.query.filter(sqlalchemy.text(query)).all()
        else:
            # consider game category
            games = (Game.query.filter(sqlalchemy.text(query)).filter(
                Game.categories.any(GameCategory.id == game_category)).all())
    return render_template('game-finder.html', games=games, all_categories=all_categories)


@app.route('/api/games')
def api_games():
    """Return list of games, with all their attributes, satisfying the criteria provided in the request query string.

    Valid query args are of two types: ownership type and game-attribute type. The function first builds two sets of
    games, ownership set with games satisfying the ownership criteria and game-attribute set with games satisfying
    the game-attribute criteria; an intersection of these two sets is then returned to the user. Specifying no criteria
    of a given type will result in the corresponding set with all the games in the database.

    Valid arguments are as follows:
        ownership:
            club=1 | include all games owned by the club
            user=INTEGER | value denotes user id | include all games owned by the user | multiple args=YES
        game-attribute:
            id=INTEGER | value denotes game id | multiple args=YES
            name=NAME
            category=INTEGER | value denotes category id | multiple args=YES
            rating-min=[1-10]
            players-from=INTEGER | query must also include players-to
            players-to=INTEGER | query must also include players-from
            time-from=INTEGER
            time-to=INTEGER
            weight-min=[1-5]
            weight-max=[1-5]

    The response is in JSON.
    """
    if not validate_api_game_query(request.args):
        return error_response('One or more query parameters have invalid key and/or value', 400)
    # club filter
    games_club = []
    if request.args.get('club') == '1':
        games_club = [club_game.game_id for club_game in db_session.query(clubs_games_assoc).all()]
    print 'games_club', games_club
    # user filter
    users = [int(user_id) for user_id in request.args.getlist('user')]
    games_user = [game.game_id for game in
                  db_session.query(users_games_assoc)
                      .filter(users_games_assoc.c.user_id.in_(users)).all()]
    print 'games_user', games_user
    # attribute filter
    query = ''
    for key, value in request.args.iteritems(multi=True):
        query = game_query_builder(key, value, query)
    query = query[:-5]
    categories = request.args.getlist('category')
    if len(categories) == 0:
        attr_games = Game.query.filter(sqlalchemy.text(query)).all()
    else:
        # consider game categories
        attr_games = (Game.query.filter(sqlalchemy.text(query)).filter(
            Game.categories.any(GameCategory.id.in_(categories))).all())
    attr_games = [game.id for game in attr_games]
    print 'games_query', attr_games
    # union of club and user games
    owned_games = set(games_club) | set(games_user)
    print 'union', owned_games
    # intersection of owned_games and attr_games
    games_id = (set(attr_games) & owned_games) if len(owned_games) > 0 else set(attr_games)
    print 'intersection', games_id
    games = Game.query.filter(Game.id.in_(games_id)).all()
    games_dict = sql_to_dicts(*games)
    return jsonify(games=games_dict)


@app.route('/api/info')
def api_info():
    """Return basic information on all sql entries of chosen types.

    Valid query args:
        users=1
        categories=1
        games=1

    The response is in JSON.
    """
    d = {
        'users': User.query.all(),
        'categories': GameCategory.query.all(),
        'games': Game.query.all()
    }
    info = {}
    for key, value in request.args.iteritems():
        if d.get(key) and value == '1':
            sql_all_dict = sql_to_dicts(*d[key])
            info[key] = dicts_purge(sql_all_dict, *['id', 'name', 'year_published'])
    return jsonify(**info)


if __name__ == '__main__':
    app.secret_key = '\xa7B\xf8w\x13\xcb\x12\x07\xd5\x95_C\x91\xd5\x8c\xf6\\\xb3\xb7\x16\x0b\xab+\x94'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)