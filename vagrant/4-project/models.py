from sqlalchemy import Column, ForeignKey, Integer, String, Numeric
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(80), nullable=False)
    name = Column(String(80), nullable=False)
    about = Column(String(1000))
    picture = Column(String(80))


class Game(Base):
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
    __tablename__ = 'game_categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)


class UserGame(Base):
    __tablename__ = 'user_games'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    game_id = Column(Integer, ForeignKey('games.id'))
    user_rating = Column(Integer)


class ClubGame(Base):
    __tablename__ = 'club_games'
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('games.id'))


class Club(Base):
    __tablename__ = 'clubs'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    about = Column(String(1000))
    picture = Column(String(80))


class ClubAdmin(Base):
    __tablename__ = 'club_admins'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))


class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    subject = Column(String(80), nullable=False)
    body = Column(String(1000), nullable=False)
    posted = Column(Integer, nullable=False)
    edited = Column(Integer)
