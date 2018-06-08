from flask import Flask, render_template

app = Flask(__name__)


# dummy database objects
dominion = {
    'name': 'Dominion',
    'year': 2008,
    'image': 'https://cf.geekdo-images.com/original/img/oN8CHUZ8CF6P1dFnhMCJXvE8SOk=/0x0/pic394356.jpg',
    'category': ['Card Game', 'Medieval'],
    'mechanic': ['Card Drafting', 'Deck Building', 'Hand Management'],
    'age': 13,
    'weight': 2.4,
    'time_min': 30,
    'time_max': 30,
    'players_min': 2,
    'players_max': 4,
    'link': 'https://boardgamegeek.com/boardgame/36218/dominion',
    'rating': 7.7,  # app's community average rating
    'owned': 3,  # list of owners
}

stone_age = {
    'name': 'Stone Age',
    'year': 2008,
    'image': 'https://cf.geekdo-images.com/original/img/Dt2tBgnvuWww89kSQqOW0vvEJr4=/0x0/pic1632539.jpg',
    'category': ['Dice', 'Prehistoric'],
    'mechanic': ['Dice Rolling', 'Set Collection', 'Worker Placement'],
    'age': 10,
    'weight': 2.5,
    'time_min': 60,
    'time_max': 90,
    'players_min': 2,
    'players_max': 4,
    'link': 'https://boardgamegeek.com/boardgame/34635/stone-age',
    'rating': 7.6,  # app's community average rating
    'owned': 2,  # list of owners
}

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
    return render_template('club.html', club=game_club, posts=[post_1, post_2], members=[user_1], games=[dominion, stone_age])


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
    return render_template('user.html', user=user_1, games=[dominion, stone_age])


@app.route('/users/<int:user_id>/edit')
def edit_user(user_id):
    return 'edit user profile'


@app.route('/users/<int:user_id>/delete')
def delete_user(user_id):
    return 'delete user profile'


@app.route('/games/new')
def new_game():
        return 'add new game'


@app.route('/games/<int:game_id>')
def game(game_id):
        return render_template('game.html', game=dominion)


@app.route('/games/<int:game_id>/edit')
def edit_game(game_id):
        return 'edit game'


@app.route('/games/<int:game_id>/delete')
def delete_game(game_id):
        return 'delete game'


@app.route('/gamefinder')
def game_finder():
    return render_template('game-finder.html', games=[dominion, stone_age])


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)