from sqlalchemy import Column, ForeignKey, Integer, String, Numeric
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """This class defines attributes of user profile and metadata of the table to which this class is mapped.

    Attributes:
        id (int): user's id
        email (str): user's email address
        name (str): user's name
        about (str): text of the 'about' paragraph in the user's profile
        picture (str): URL of the user's profile picture
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(80), nullable=False)
    name = Column(String(80), nullable=False)
    about = Column(String(1000))
    picture = Column(String(80))


class Game(Base):
    """This class defines attributes of board game and metadata of the table to which this class is mapped.

    Attributes:
       id (int): games's id
       name (str): games's name
       year_published (int): year in which the game was published
       image (str): URL of the game picture on BoardGameGeek(BGG)
       category_1 (int): id of a category to which this game belongs
       category_2 (int): id of a category to which this game belongs
       category_3 (int): id of a category to which this game belongs
       min_age (int): minimum recommended player's age
       weight (float): game's complexity rating
       min_playtime (int): minimum game playtime in minutes
       max_playtime (int): maximum game playtime in minutes
       min_players (int): minimum number of players
       max_players (int): maximum number of players
       rating (float): game's average rating; attribute currently not used
       bgg_rating (float): game's average rating on BGG
       bgg_id (int): game's id on BGG
       bgg_link (str): URL of the game's page on BGG
    """
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    year_published = Column(Integer, nullable=False)
    image = Column(String(80), nullable=False)
    category_1 = Column(Integer, ForeignKey('game_categories.id'))
    category_2 = Column(Integer, ForeignKey('game_categories.id'))
    category_3 = Column(Integer, ForeignKey('game_categories.id'))
    min_age = Column(Integer)
    weight = Column(Numeric(4, 3))
    min_playtime = Column(Integer)
    max_playtime = Column(Integer)
    min_players = Column(Integer)
    max_players = Column(Integer)
    rating = Column(Numeric(4, 3))
    bgg_rating = Column(Numeric(4, 3))
    bgg_id = Column(Integer)
    bgg_link = Column(String(80))


class GameCategory(Base):
    """This class defines attributes of game-category and metadata of the table to which this class is mapped.

    Attributes:
        id (int): category id
        name (str): category name
    """
    __tablename__ = 'game_categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)


class UserGame(Base):
    """This class defines attributes of user's physical copy of a board game and metadata of the table to which this
    class is mapped.

    Attributes:
        id (int): id of the physical copy of the game
        user_id (int): id of the owner of the game
        game_id (int): game's id
        user_rating (int): owner's rating of the game; attribute currently not used
    """
    __tablename__ = 'user_games'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    game_id = Column(Integer, ForeignKey('games.id'))
    user_rating = Column(Integer)


class ClubGame(Base):
    """This class defines attributes of club's physical copy of a board game and metadata of the table to which this
    class is mapped.

    Attributes:
        id (int): id of the physical copy of the game
        game_id (int): game's id
    """
    __tablename__ = 'club_games'
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('games.id'))


class Club(Base):
    """This class defines attributes of club profile and metadata of the table to which this class is mapped.

        Attributes:
            id (int): club's id
            name (str): name of the club; attribute currently not used
            about (str): text of the 'about' paragraph in the club's profile
            picture (str): URL of the club's profile picture; attribute currently not used
        """
    __tablename__ = 'clubs'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    about = Column(String(1000))
    picture = Column(String(80))


class ClubAdmin(Base):
    """This class defines attributes of club's admin and metadata of the table to which this class is mapped.

        Attributes:
            id (int): admin's id
            user_id (int): id of the user who is the admin
        """
    __tablename__ = 'club_admins'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))


class Post(Base):
    """This class defines attributes of post and metadata of the table to which this class is mapped.

        Attributes:
            id (int): post's id
            user_id (int): id of the author of the post
            subject (str): subject of the post
            body (str): body of the post
            posted (int): time in seconds elapsed between the epoch and the creation of the post
            edited (int): time in seconds elapsed between the epoch and the last update of the post
        """
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    subject = Column(String(80), nullable=False)
    body = Column(String(1000), nullable=False)
    posted = Column(Integer, nullable=False)
    edited = Column(Integer)
