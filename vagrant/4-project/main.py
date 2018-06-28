from flask import Flask, render_template, url_for, request, redirect, session, abort, make_response
from database import db_session
from models import Club, ClubGame, Game, Post,  User, UserGame, GameCategory
import requests
from xml.etree import ElementTree
import sqlalchemy
from oauth2client import client
import json
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
    for post in posts:
        user = User.query.filter_by(id=post.user_id).scalar()
        post_dict = {
            'id': post.id,
            'subject': post.subject,
            'body': post.body,
            'author': user.name,
            'posted': time.strftime("%d/%m/%Y, %H:%M", time.gmtime(post.posted)),
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


def init_club_info():
    club = Club(name='Board Game Club')
    db_session.add(club)
    db_session.commit()


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
    return render_template('club.html', club=club, posts=posts_read, members=members, games=games, categories=categories)


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
        bgg_options = bgg_game_options(request.args.get('name'))
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


@app.route('/gdisconnect')
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
        print session
        return json_response({'msg': 'Successfully disconnected'}, 200)
    else:
        print r.text
        return error_response('Failed to revoke access token', 500)


@app.route('/users/<int:user_id>/new')
def profile_add(user_id):
    user = get_user(user_id)
    return render_template('profile-new.html', user=user)


@app.route('/users/<int:user_id>', methods=['GET', 'PATCH', 'DELETE'])
def profile_(user_id):
    user = get_user(user_id)
    if request.method == 'GET':
        user_games = get_user_games(user_id)
        games_id = []
        for user_game in user_games:
            games_id.append(user_game.game_id)
        query = 'id in {}'.format(games_id)
        query = multi_replace(query, {'[': '(', ']': ')'})
        games = Game.query.filter(sqlalchemy.text(query)).all()
        categories = category_dict(games)
        return render_template('profile.html', user=user, games=games, categories=categories)
    elif request.method == 'PATCH':
        attributes = request.get_json()['data']['attributes']
        patch_resource(attributes, user)
        return '', 204
    else:
        db_session.delete(user)
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
        bgg_options = bgg_game_options(request.args.get('name'))
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
    db_session.delete(user_game)
    db_session.commit()
    clear_games(game_id)
    return '', 204


@app.route('/games/<int:game_id>', methods=['GET', 'POST'])
def game_(game_id):
    bgame = get_game(game_id)
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