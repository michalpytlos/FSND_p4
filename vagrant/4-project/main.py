from flask import Flask, render_template, url_for, request, redirect
from database import db_session
from models import Club, ClubGame, Game, Post,  User, UserGame
import requests
from xml.etree import ElementTree
import sqlalchemy

app = Flask(__name__)


# Remove database session at the end of each request
@app.teardown_appcontext
def remove_session(exception=None):
    db_session.remove()


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
            category = categories[i]
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
    return 'sign in'


@app.route('/signout')
def sign_out():
    return 'sign out'


@app.route('/users/new')
def new_user():
    return render_template('user-create.html', user=user_1)


@app.route('/users/<int:user_id>')
def user(user_id):
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
    return render_template('game.html', game=bgame, game_id=game_id)


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
    return render_template('game-finder.html', games=[])


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)