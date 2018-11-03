#!/usr/bin/env python2.7
"""InitDB program.

To be run as a script.

Part of the BoardGameClub app.
"""
from boardgameclub.database import Base, engine, db_session
from boardgameclub.models import Club


def init_club_info():
    """Add Board Game Club to the database."""
    club = Club(name='Board Game Club')
    db_session.add(club)
    db_session.commit()


def init_db():
    """Initialize database."""
    import boardgameclub.models
    Base.metadata.create_all(bind=engine)


def main():
    init_db()
    init_club_info()
    print 'Database initialized'


if __name__ == '__main__':
    main()
