#!/usr/bin/env python2.7
"""AddAdmin program.

To be run as a script.

Part of the BoardGameClub app.
"""
from boardgameclub.database import db_session
from boardgameclub.models import User, ClubAdmin


def add_club_admin(user_email):
    """Add user to club admins."""
    user = User.query.filter_by(email=user_email).scalar()
    if not user:
        print 'User not found'
    elif user.club_admin:
        print 'User is already an admin'
    else:
        admin = ClubAdmin(user_id=user.id)
        db_session.add(admin)
        db_session.commit()
        print 'User added to club admins'


def main():
    # Add user to club admins
    email = raw_input(
        'Add user to club admins by entering his/her email address: ')
    add_club_admin(email)


if __name__ == '__main__':
    main()
