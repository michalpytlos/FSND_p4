from flask import Flask, render_template, url_for, request, redirect, session, abort, make_response, jsonify
from database import db_session
from models import Club, ClubGame, Game, Post,  User, UserGame, GameCategory, ClubAdmin
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
    # csrf protection as per:
    # 'http://flask.pocoo.org/snippets/3/' posted by Dan Jacob on 2010-05-03 @ 11:29 and filed in Security
    # but with only one token per session
    if request.method in ('POST', 'PATCH', 'DELETE'):
        print 'validating csrf token'
        print 'session: {}'.format(session)
        token = session.get('_csrf_token')
        if not token or token not in (request.form.get('_csrf_token'),
                                      request.get_json().get('_csrf_token') if request.get_json() else None):
            print 'failed csrf token test'
            abort(403)
        else:
            print 'csrf token ok'


def generate_csrf_token():
    if '_csrf_token' not in session:
        print 'generating csrf token'
        session['_csrf_token'] = random_string()
    return session['_csrf_token']


app.jinja_env.globals['csrf_token'] = generate_csrf_token


def random_string():
    # create random string
    chars = string.ascii_letters + string.digits
    return ''.join([chars[random.randint(0, 61)] for i in range(20)])


# Remove database session at the end of each request
@app.teardown_appcontext
def remove_session(exception=None):
    db_session.remove()


@app.before_request
def ownership_required():
    # restrict access to the owner of the resource only
    if request.endpoint in ('profile_game_add', 'club_game_add') or request.method in ('PATCH', 'DELETE'):
        print 'checking ownership'
        if 'user_id' not in session or not check_ownership():
            abort(403)
        else:
            print 'ownership ok'


def check_ownership():
    # check if the user is the owner of the requested resource
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
    # restrict access to logged in users only
    if (
        (request.endpoint in ('post_add', 'profile_add', 'g_disconnect') or
         request.endpoint == 'game_' and request.method == 'POST') and
        'username' not in session
    ):
        return redirect('/signin')


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


def json_response(body, code):
    # build a json response
    j_response = make_response(json.dumps(body), code)
    j_response.headers['Content-Type'] = 'application/json'
    return j_response


def error_response(err_msg, code):
    # build an error json response
    err_response = make_response(json.dumps({"error-msg": err_msg}), code)
    err_response.headers['Content-Type'] = 'application/json'
    return err_response


def bgg_game_options(bg_name):
    # Search for games on bgg API by name
    # Return list of dictionaries. Each dictionary holds basic info about a game.
    bgg_games = []
    url = 'https://boardgamegeek.com/xmlapi2/search'
    payload = {'query': bg_name, 'type': 'boardgame'}
    r = requests.get(url, params=payload)
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


def check_user(email, name, picture):
    # Check if the user is already in the database. If not, make a new entry.
    # return user's id
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


def get_user(user_id):
    return User.query.filter_by(id=user_id).scalar()


def get_user_games(user_id):
    return UserGame.query.filter_by(user_id=user_id).all()


def category_dict(bgames):
    # return dictionary where each key is a game id and the corresponding value is a list of categories, given by name,
    # to which this game belongs
    categories = {}
    for bgame in bgames:
        categories[str(bgame.id)] = get_categories(bgame)
    return categories


def make_posts_read(posts):
    # return list of post dictionaries where each dictionary holds data in a format ready to be used in the template
    posts_read = []
    user_id = session.get('user_id')
    for post in posts:
        user = User.query.filter_by(id=post.user_id).scalar()
        post_dict = {
            'id': post.id,
            'subject': post.subject,
            'body': post.body,
            'author': user.name,
            'posted': time.strftime("%d/%m/%Y, %H:%M", time.gmtime(post.posted)),
            'owner': post.user_id == user_id
        }
        if post.edited:
            post_dict['edited'] = time.strftime("%d/%m/%Y, %H:%M", time.gmtime(post.edited))
        posts_read.append(post_dict)
    return posts_read


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


def game_query_builder(key, value, query):
    # modify textual sql query in order take into account an additional constraint
    # the constraint is to be provided in the form of a key-value pair
    d = {'id': "id in ({value})",
         'name': "name LIKE '{value}%'",
         'category': "(category_1 in ({value}) OR category_2 in ({value}) OR category_3 in ({value}))",
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
    elif key == 'category' and 'category_' in query:
        for category in ['category_1', 'category_2', 'category_3']:
            pos = query.find(')', query.find(category))
            query = query[:pos] + ', ' + value + query[pos:]
        return query
    else:
        return query + d[key].format(value=value) + ' AND '


def multi_replace(my_string, repl_dict):
    for key, value in repl_dict.iteritems():
        my_string = my_string.replace(key, value)
    return my_string


def clear_games(*games_id):
    # If the game is not owned by any user or the club, remove it from the database
    for game_id in games_id:
        user_game = UserGame.query.filter_by(game_id=game_id).first()
        club_game = ClubGame.query.filter_by(game_id=game_id).first()
        if not user_game and not club_game:
            bgame = get_game(game_id)
            db_session.delete(bgame)
    db_session.commit()


def patch_resource(attributes, my_obj):
    # Patch database resource
    for attribute in attributes:
        setattr(my_obj, attribute['name'], attribute['value'])
    db_session.add(my_obj)
    db_session.commit()


def validate_api_game_query(query_dict):
    """ validate keys and values of the query """
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
    # remove all keys not in keep_keys from each dictionary
    for p_dict in p_dicts:
        for key in p_dict.keys():
            if key not in keep_keys:
                del p_dict[key]
    return p_dicts


def sql_to_dicts(*games):
    # convert a list of database objects to list of dictionaries
    # each column-name-column-value pair in an object is converted to a key-value pair in the corresponding dictionary
    sql_dicts = []
    for game in games:
        keys = game.__table__.columns.keys()
        values = [getattr(game, key) for key in keys]
        values = [float(value) if type(value) == Decimal else value for value in values]
        sql_dicts.append(dict(zip(keys, values)))
    return sql_dicts


def init_club_info():
    club = Club(name='Board Game Club')
    db_session.add(club)
    db_session.commit()


def add_club_admin(email):
    # Add user to club admins
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
    club = Club.query.filter_by(id=1).scalar()
    members = User.query.all()
    club_games = ClubGame.query.all()
    games_id = []
    for club_game in club_games:
        games_id.append(club_game.game_id)
    query = 'id in {}'.format(games_id)
    query = multi_replace(query, {'[': '(', ']': ')'})
    games = Game.query.filter(sqlalchemy.text(query)).all()
    categories = category_dict(games)
    posts = Post.query.all()
    posts_read = make_posts_read(posts)
    return render_template('club.html', club=club, posts=posts_read, members=members, games=games,
                           categories=categories, owner=check_ownership())


@app.route('/club', methods=['PATCH'])
def club_():
    club = Club.query.filter_by(id=1).scalar()
    attributes = request.get_json()['data']['attributes']
    patch_resource(attributes, club)
    return '', 204


@app.route('/club/games/add', methods=['GET', 'POST'])
def club_game_add():
    if request.method == 'GET':
        # Show the game options matching the specified name
        bgg_options = bgg_game_options(request.args['name'])
        return render_template('game-options.html', games=bgg_options)
    else:
        # Add the chosen game to the database
        game_id = check_game(request.form['bgg-id'])
        club_game = ClubGame(game_id=game_id)
        db_session.add(club_game)
        db_session.commit()
        return redirect(url_for('home'))


@app.route('/club/games/<int:game_id>', methods=['DELETE'])
def club_game_(game_id):
    club_game = ClubGame.query.filter_by(game_id=game_id).first()
    try:
        assert club_game is not None
    except AssertionError:
        abort(404)
    db_session.delete(club_game)
    db_session.commit()
    clear_games(game_id)
    return '', 204


@app.route('/posts/add', methods=['GET', 'POST'])
def post_add():
    if request.method == 'GET':
        return render_template('post-new.html')
    else:
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
    post = Post.query.filter_by(id=post_id).scalar()
    if request.method == 'PATCH':
        attributes = request.get_json()['data']['attributes']
        attributes.append({'name': 'edited', 'value': int(time.time())})
        patch_resource(attributes, post)
        return '', 204
    else:
        db_session.delete(post)
        db_session.commit()
        return '', 204


@app.route('/gconnect', methods=['POST'])
def g_connect():
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
    print session
    # check if user is connected
    if 'access_token' not in session:
        return error_response('Access token missing', 401)
    # revoke access token
    r = requests.post('https://accounts.google.com/o/oauth2/revoke',
                      params={'token': session['access_token']},
                      headers={'content-type': 'application/x-www-form-urlencoded'})
    # delete user info from session
    if r.status_code == 200:
        del session['email']
        del session['username']
        del session['access_token']
        del session['user_id']
        del session['_csrf_token']
        print session
        return json_response({'msg': 'Successfully disconnected'}, 200)
    else:
        print r.text
        return error_response('Failed to revoke access token', 500)


@app.route('/users/<int:user_id>/new')
def profile_add(user_id):
    try:
        user = User.query.filter_by(id=user_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        abort(404)
    return render_template('profile-new.html', user=user)


@app.route('/users/<int:user_id>', methods=['GET', 'PATCH', 'DELETE'])
def profile_(user_id):
    try:
        user = User.query.filter_by(id=user_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        abort(404)  # can be raised only on GET request; PATCH and DELETE are protected by check_ownership()
    if request.method == 'GET':
        user_games = get_user_games(user_id)
        games_id = []
        for user_game in user_games:
            games_id.append(user_game.game_id)
        query = 'id in {}'.format(games_id)
        query = multi_replace(query, {'[': '(', ']': ')'})
        games = Game.query.filter(sqlalchemy.text(query)).all()
        categories = category_dict(games)
        return render_template('profile.html', user=user, games=games, categories=categories, owner=check_ownership())
    elif request.method == 'PATCH':
        attributes = request.get_json()['data']['attributes']
        patch_resource(attributes, user)
        return '', 204
    else:
        db_session.delete(user)
        # delete all posts for this user
        Post.query.filter_by(user_id=user_id).delete()
        # remove the user from club admins
        ClubAdmin.query.filter_by(user_id=user_id).delete()
        # delete all user_games for this user
        user_games = UserGame.query.filter_by(user_id=user_id).all()
        games_id = []
        for user_game in user_games:
            db_session.delete(user_game)
            games_id.append(user_game.game_id)
        db_session.commit()
        clear_games(*games_id)
        return '', 204


@app.route('/users/<int:user_id>/games/add', methods=['GET', 'POST'])
def profile_game_add(user_id):
    if request.method == 'GET':
        # Show the game options matching the specified name
        bgg_options = bgg_game_options(request.args['name'])
        return render_template('game-options.html', games=bgg_options)
    else:
        # Add the chosen game to the database
        game_id = check_game(request.form['bgg-id'])
        user_game = UserGame(user_id=user_id, game_id=game_id)
        db_session.add(user_game)
        db_session.commit()
        return redirect(url_for('profile_', user_id=user_id))


@app.route('/users/<int:user_id>/games/<int:game_id>', methods=['DELETE'])
def profile_game_(user_id, game_id):
    user_game = UserGame.query.filter_by(user_id=user_id, game_id=game_id).first()
    try:
        assert user_game is not None
    except AssertionError:
        abort(404)
    db_session.delete(user_game)
    db_session.commit()
    clear_games(game_id)
    return '', 204


@app.route('/games/<int:game_id>', methods=['GET', 'POST'])
def game_(game_id):
    try:
        bgame = Game.query.filter_by(id=game_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        abort(404)
    if request.method == 'GET':
        categories = get_categories(bgame)
        return render_template('game.html', game=bgame, game_id=game_id, categories=categories)
    else:
        # Update game info from bgg API
        game_info = bgg_game_info(bgame.bgg_id)
        for key, value in game_info.iteritems():
            setattr(bgame, key, value)
        db_session.commit()
        return redirect(url_for('game_', game_id=game_id))


@app.route('/games/search')
def game_finder():
    all_categories = GameCategory.query.all()
    games = []
    categories = {}
    if len(request.args) > 0:
        query = ''
        for key, value in request.args.iteritems():
            query = game_query_builder(key, value, query)
        query = query[:-5]
        print query
        games = Game.query.filter(sqlalchemy.text(query)).all()
        categories = category_dict(games)
    return render_template('game-finder.html', games=games, all_categories=all_categories, categories=categories)


@app.route('/api/games')
def api_games():
    """
    return list of game JSON objects satisfying the criteria provided in the request query string
    query params are divided into two groups: ownership and game attributes
    endpoint returns intersection of ownership and attributes sets

    ownership params:   club=1 | include all games owned by the club
                        user=INTEGER | value denotes user id | include all games owned by the user | multiple args=YES
    game attribute args:
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
    """
    if not validate_api_game_query(request.args):
        return error_response('One or more query parameters have invalid key and/or value', 400)
    # club filter
    games_club = []
    if request.args.get('club') == '1':
        games_club = [game.game_id for game in ClubGame.query.all()]
    print 'games_club', games_club
    # user filter
    users = [int(user_id) for user_id in request.args.getlist('user')]
    games_user = [game.game_id for game in UserGame.query.filter(UserGame.user_id.in_(users)).all()]
    print 'games_user', games_user
    # attribute filter
    query = ''
    for key, value in request.args.iteritems(multi=True):
        query = game_query_builder(key, value, query)
    query = query[:-5]
    attr_games = [game.id for game in Game.query.filter(sqlalchemy.text(query)).all()]
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
    # return basic information on all sql entries of a chosen type
    # accepted request query params: users=1, categories=1 and games=1
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