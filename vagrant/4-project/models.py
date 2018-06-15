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
    category_1 = Column(String(80))
    category_2 = Column(String(80))
    category_3 = Column(String(80))
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
    email = Column(String(80), nullable=False)
    name = Column(String(80), nullable=False)
    about = Column(String(1000))
    picture = Column(String(80))


class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    subject = Column(String(80), nullable=False)
    body = Column(String(1000), nullable=False)
    time = Column(Integer, nullable=False)