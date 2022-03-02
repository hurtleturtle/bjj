#!/usr/bin/env python3
import os
from argparse import ArgumentParser
import shlex
import pandas as pd
from getpass import getpass
from nexusbjj.db import Database, QueryResult
from datetime import datetime, timedelta
from numpy.random import randint
import calendar


def get_args():
    parser = ArgumentParser()
    parser.add_argument('-a', '--admin', type=int, default=None,
                        help='Give user specified with -u admin privileges: 0' +
                        ' - none, 1 - read-only, 2 - read-write')
    parser.add_argument('-l', '--list', action='store_true', help='List users')
    parser.add_argument('-u', '--email', help='email of user to act on')
    parser.add_argument('-i', '--user-id', type=int, help='ID of user')
    parser.add_argument('-e', '--execute-script', help='Execute SQL script')
    parser.add_argument('-q', '--query', help='Execute custom query')
    parser.add_argument('--add-attendances', type=int, help='Add random attendances')
    parser.add_argument('--commit', action='store_true', help='Commit query changes to database')
    parser.add_argument('--db-user', default='webapp', help='Database user')
    parser.add_argument('--db-pass', help='Password to login to database')
    parser.add_argument('--db-host', help='IP address of database')
    parser.add_argument('--reset-password', action='store_true', help='Reset password for user')

    return parser.parse_args()


def get_database_details(host, user, password, config_path='instance/config.py'):
    if not all((host, user, password)):
        config = {}
        try:
            with open(config_path) as f:
                for line in f:
                    key, equals, value = shlex.split(line)
                    config[key] = value
            host = config.get('DATABASE_HOST') if not host else host
            user = config.get('DATABASE_USER') if not user else user
            password = config.get('DATABASE_PASS') if not password else password
        except OSError:
            print(f'Error reading database details from {config_path}. Please supply DB details.')
            exit()
    
    details = {
        'db_host': host,
        'db_user': user,
        'db_pass': password
    }
    return details


def print_results(rows, err_message='No results returned'):
    try:
        print(pd.DataFrame(rows, columns=rows[0].keys()))
    except IndexError:
        print(err_message)


if __name__ == '__main__':
    args = get_args()
    db = Database(**get_database_details(args.db_host, args.db_user, args.db_pass))

    try:
        user = db.get_user(uid=args.user_id, name=args.email)
    except Exception:
        user = None

    if args.admin is not None:
        if user:
            db.make_admin(user['id'], admin_level=args.admin)
        else:
            print('Invalid email and/or user ID')

    if args.list:
        users = db.get_users()
        print_results(users)

    if args.execute_script:
        with open(args.execute_script) as f:
            db.executescript(f.read())
        print('Database updated.')
        
    if args.add_attendances:
        classes = QueryResult(db.get_all_classes())
        users = QueryResult(db.get_users(('id',)))
        query = 'INSERT INTO attendance (user_id, class_id, class_date, class_time, date) VALUES (%s, %s, %s, %s, %s);'
        results = QueryResult()
        
        for idx in range(args.add_attendances):
            user_id = users.sample().to_dict('records')[0]['id']
            _class = classes.sample().to_dict('records')[0]
            attendance_date = datetime(year=randint(2021, 2023), month=randint(1, 13), day=randint(1, 29),
                                       hour=randint(0, 24), minute=randint(0, 60), second=randint(0, 60))
            weekday = _class['weekday']
            
            if attendance_date.strftime('%A') != weekday:
                attendance_date = attendance_date + timedelta(days=(list(calendar.day_name).index(weekday) -
                                                              attendance_date.weekday()))
            if attendance_date > datetime.today():
                attendance_date = attendance_date - timedelta(days=365)
            
            params = (user_id, _class['id'], attendance_date.date(), _class['class_time'], attendance_date)
            db.execute(query, params)
            db.commit()
            _class['user'] = user_id
            _class['attended'] = attendance_date.isoformat()
            results = pd.concat([results, QueryResult(_class, index=[0])], ignore_index=True)
        
        print(results)

    if args.reset_password:
        if user:
            password = getpass(f'Enter new password for {user["email"]}: ')
            if password == getpass('Re-enter password to confirm change: '):
                db.change_password(user['id'], password)
        else:
            print('Please specify the user whose password you want to reset.')
        
    if args.query:
        db.execute(args.query)
        results = db.cursor.fetchall()
        print_results(results)

        if args.commit:
            db.commit()
