from flask import Flask

app = Flask(__name__)


@app.route('/')
def home():
        return 'home page'


@app.route('/signin')
def sign_in():
    return 'sign in'


@app.route('/signout')
def sign_out():
    return 'sign out'


@app.route('/clubs/<int:club_id>')
def club(club_id):
        return 'club page'


@app.route('/clubs/new')
def new_club():
        return 'add new club'


@app.route('/users/<int:user_id>')
def user(user_id):
        return 'user page'


@app.route('/users/new')
def new_user():
        return 'add new user'


@app.route('/games/<int:game_id>')
def game(game_id):
        return 'game page'


@app.route('/games/new')
def new_game():
        return 'add new game'


@app.route('/gamefinder')
def game_finder():
        return 'game finder page'


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)