"""SQLAlchemy model and table definitions."""

from sqlalchemy import Table, Column, ForeignKey, Integer, String, Numeric
from sqlalchemy.orm import relationship
from boardgameclub.database import Base


users_games_assoc = Table(
    'users_games',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('game_id', Integer, ForeignKey('games.id'))
)


clubs_games_assoc = Table(
    'clubs_games',
    Base.metadata,
    Column('club_id', Integer, ForeignKey('clubs.id')),
    Column('game_id', Integer, ForeignKey('games.id'))
)


games_categories_assoc = Table(
    'games_categories',
    Base.metadata,
    Column('game_id', Integer, ForeignKey('games.id')),
    Column('category_id', Integer, ForeignKey('game_categories.id'))
)


class User(Base):
    """This class defines attributes of user profile and metadata of the
    table to which this class is mapped.

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
    games = relationship("Game",
                         secondary=users_games_assoc,
                         back_populates="users")
    posts = relationship("Post",
                         cascade="all, delete-orphan",
                         back_populates="author")
    club_admin = relationship("ClubAdmin",
                              uselist=False,
                              cascade="all, delete-orphan")


class Game(Base):
    """This class defines attributes of board game and metadata of the
    table to which this class is mapped.

    Attributes:
       id (int): games's id
       name (str): games's name
       year_published (int): year in which the game was published
       image (str): URL of the game picture on BoardGameGeek(BGG)
       min_age (int): minimum recommended player's age
       weight (float): game's complexity rating
       min_playtime (int): minimum game playtime in minutes
       max_playtime (int): maximum game playtime in minutes
       min_players (int): minimum number of players
       max_players (int): maximum number of players
       bgg_rating (float): game's average rating on BGG
       bgg_id (int): game's id on BGG
       bgg_link (str): URL of the game's page on BGG
    """
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    year_published = Column(Integer, nullable=False)
    image = Column(String(80), nullable=False)
    min_age = Column(Integer)
    weight = Column(Numeric(4, 3))
    min_playtime = Column(Integer)
    max_playtime = Column(Integer)
    min_players = Column(Integer)
    max_players = Column(Integer)
    bgg_rating = Column(Numeric(4, 3))
    bgg_id = Column(Integer)
    bgg_link = Column(String(80))
    categories = relationship("GameCategory",
                              secondary=games_categories_assoc,
                              back_populates="games")
    users = relationship("User",
                         secondary=users_games_assoc,
                         back_populates="games")
    clubs = relationship("Club",
                         secondary=clubs_games_assoc,
                         back_populates="games")


class GameCategory(Base):
    """This class defines attributes of game-category and metadata of
    the table to which this class is mapped.

    Attributes:
        id (int): category id
        name (str): category name
    """
    __tablename__ = 'game_categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    games = relationship("Game",
                         secondary=games_categories_assoc,
                         back_populates="categories")


class Club(Base):
    """This class defines attributes of club profile and metadata of the
    table to which this class is mapped.

        Attributes:
            id (int): club's id
            name (str): name of the club; attribute currently not used
            about (str): text of the 'about' paragraph in the club's profile
            picture (str): URL of the club's profile picture; not used
        """
    __tablename__ = 'clubs'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    about = Column(String(1000))
    picture = Column(String(80))
    games = relationship("Game",
                         secondary=clubs_games_assoc,
                         back_populates="clubs")


class ClubAdmin(Base):
    """This class defines attributes of club's admin and metadata of
    the table to which this class is mapped.

        Attributes:
            id (int): admin's id
            user_id (int): id of the user who is the admin
        """
    __tablename__ = 'club_admins'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))


class Post(Base):
    """This class defines attributes of post and metadata of the table
    to which this class is mapped.

        Attributes:
            id (int): post's id
            user_id (int): id of the author of the post
            subject (str): subject of the post
            body (str): body of the post
            posted (int): time in seconds elapsed between the epoch and
                the creation of the post
            edited (int): time in seconds elapsed between the epoch and
                the last update of the post
        """
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    subject = Column(String(80), nullable=False)
    body = Column(String(1000), nullable=False)
    posted = Column(Integer, nullable=False)
    edited = Column(Integer)
    author = relationship("User",
                          back_populates="posts")
