#!/usr/bin/env python2.7
from main import add_club_admin

if __name__ == '__main__':
    # Add user to club admins
    email = raw_input(
        'Add user to club admins by entering his/her email address: ')
    add_club_admin(email)
