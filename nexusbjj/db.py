import mysql.connector
import click
from flask import current_app, g, flash
from flask.cli import with_appcontext
from os.path import dirname, basename
import os
from werkzeug.utils import secure_filename
from shutil import rmtree
from getpass import getpass
from werkzeug.security import check_password_hash, generate_password_hash
from pandas import DataFrame
from datetime import time, timedelta, datetime
from time import localtime, strftime
from numpy import isnan


class Database:
    def __init__(self, db_name='nexusbjj', db_host=None, db_user=None, db_pass=None):
        self.db_name = db_name
        self.db = self.connect(db_host, db_user, db_pass)
        self.cursor = self.db.cursor(dictionary=True)
        self.execute = self.cursor.execute
        self.commit = self.db.commit
        self.close = self.db.close
        self.executemany = self.cursor.executemany
        self.challenge_parent_folder = 'challenges'
        self.check_schema()

    def connect(self, db_host=None, db_user=None, db_pass=None):
        db_host = db_host if db_host else current_app.config['DATABASE_HOST']
        db_user = db_user if db_user else current_app.config['DATABASE_USER']
        db_pass = db_pass if db_pass else (current_app.config['DATABASE_PASS']\
             if current_app.config['DATABASE_PASS'] else getpass('Enter database password: '))
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=self.db_name,
            connection_timeout=2
        )
        return connection

    def executescript(self, script):
        results = self.execute(script, multi=True)
        
        if results:
            for result in results:
                print(result)
        self.commit()

    def check_schema(self):
        query = 'SELECT table_name FROM information_schema.tables WHERE table_schema = %s'
        params = ('nexusbjj',)
        self.execute(query, params)
        tables = self.cursor.fetchall()

        # if len(tables) != 9:
        #     with current_app.open_resource('schema.sql') as f:
        #         self.executescript(f.read().decode('utf8'))

    def make_admin(self, uid, admin_level=0):
        levels = {0: 'no', 1: 'read', 2: 'read-write'}
        query = 'UPDATE users SET admin = %s WHERE id = %s'
        params = (levels[admin_level], uid)
        self.execute(query, params)
        self.commit()

    def get_users(self, columns=('*',), conditions='', params=tuple()):
        user_columns = ', '.join(['users.' + column for column in columns])
        query = 'SELECT ' + user_columns + ', age_group_id, membership_type, age_groups.name AS age_group FROM users'
        query += ' LEFT JOIN memberships ON membership_id=memberships.id LEFT JOIN age_groups ON age_group_id=age_groups.id'
        
        if conditions:
            query += ' WHERE ' + conditions
            self.execute(query, params)
        else:
            self.execute(query)
        
        users = self.cursor.fetchall()
        return users

    def get_user(self, uid=None, email=None, columns=('*',)):
        user_columns = ', '.join(['users.' + column for column in columns])
        query = 'SELECT ' + user_columns + ', age_group_id, membership_type, age_groups.name AS age_group FROM users LEFT JOIN memberships'
        query += ' ON membership_id=memberships.id LEFT JOIN age_groups ON age_group_id=age_groups.id WHERE '
        params = tuple()

        if uid:
            query += 'users.id = %s'
            params = (uid,)
        elif email:
            query += 'email = %s'
            params = (email,)
        else:
            try:
                current_user_id = g.user['id']
                query += 'users.id = %s'
                params = (current_user_id,)
            except (RuntimeError, TypeError):
                return ''

        self.execute(query, params)
        return self.cursor.fetchone()

    def get_children(self, parent_id):
        query = 'SELECT * FROM children WHERE parent_id = %s'
        params = (parent_id, )
        self.execute(query, params)
        return self.cursor.fetchall()

    def add_child(self, first_name, last_name, parent_id):
        query = 'INSERT INTO children (first_name, last_name, parent_id) VALUES (%s, %s, %s)'
        params = (first_name, last_name, parent_id)
        self.execute(query, params)
        self.commit()

    def add_user(self, email, password, first_name, last_name, mobile_number, membership_id, admin_level='no'):
        query = 'INSERT INTO users (email, password, first_name, last_name, mobile_number, membership_id, admin)'
        query += ' VALUES (%s, %s, %s, %s, %s, %s, %s)'
        params = (email, generate_password_hash(password), first_name, last_name, mobile_number, membership_id, admin_level)
        self.execute(query, params)
        self.commit()

    def update_user(self, uid, column, value):
        query = f'UPDATE users SET {column} = %s WHERE id = %s'
        params = (value, uid)
        self.execute(query, params)
        self.commit()

    def change_password(self, uid, new_password):
        column = 'password'
        password_hash = generate_password_hash(new_password)
        self.update_user(uid, column, password_hash)

    def update_user_access_time(self, uid):
        query = 'UPDATE users SET last_access = CURRENT_TIMESTAMP WHERE id = %s'
        params = (uid,)
        self.execute(query, params)
        self.commit()

    def delete_user(self, uid):
        query = 'DELETE FROM users WHERE id = %s'
        params = (uid,)
        self.execute(query, params)
        self.commit()

    def get_coaches(self):
        query = 'SELECT id, email, first_name, last_name FROM users WHERE is_coach=true'
        self.execute(query)
        return self.cursor.fetchall()

    def add_class(self, class_name, weekday, time, duration, coach_id, age_group_id, class_type='No Gi'):
        if class_type not in ['Gi', 'No Gi']:
            flash('Invalid class type. Class type must be either Gi or No Gi')
            return False

        query = 'INSERT INTO classes (class_name, class_type, weekday, time, duration, coach_id, age_group_id) '
        query += 'VALUES (%s, %s, %s, %s, %s, %s, %s)'
        params = (class_name, class_type, weekday, time, duration, coach_id, age_group_id)
        self.execute(query, params)
        self.commit()
        return True

    def get_classes(self, weekday=None, class_time=None, age_groups=None):
        query = 'SELECT id, DATE_FORMAT(time, "%H:%i") class_time, class_name, duration, '
        query += 'DATE_FORMAT(ADDTIME(time, duration), "%H:%i") end_time, weekday, age_group_id'
        query += ' FROM classes WHERE weekday = %s AND time >= %s'
        params = []
        today = datetime.today()

        if weekday:
            params.append(weekday)
        else:
            params.append(today.strftime('%A'))

        if class_time:
            show_classes_from_time = class_time
        else:
            show_classes_from_time = '00:00:00'

        params.append(show_classes_from_time)

        if age_groups:
            if isinstance(age_groups, int) or len(age_groups) == 1:
                query += ' AND age_group_id = %s'

                if isinstance(age_groups, int):
                    params.append(age_groups)
                else:
                    params.extend(age_groups)
                print(params)
            else:
                query += ' AND age_group_id IN (' + ', '.join(['%s'] * len(age_groups)) + ')'
                params.extend(age_groups)

        self.execute(query, params)
        todays_classes = self.cursor.fetchall()
        return todays_classes

    def get_all_classes(self, conditions=None, params=None):
        query = 'SELECT id, DATE_FORMAT(time, "%H:%i") class_time, class_name, duration, '
        query += 'DATE_FORMAT(ADDTIME(time, duration), "%H:%i") end_time, weekday, age_group_id'
        query += ' FROM classes'

        if conditions:
            query += ' WHERE ' + conditions
            self.execute(query, params)
        else:
            self.execute(query)
        
        return self.cursor.fetchall()


    def check_in(self, class_id, user_id, class_date, class_time, child_id=None):
        columns = ['user_id', 'class_id', 'class_date', 'class_time']
        params = [user_id, class_id, class_date, class_time]
        
        if child_id and not isnan(child_id):
            columns.append('child_id')
            params.append(child_id)

        query = 'INSERT INTO attendance (' + ', '.join(columns) + ') VALUES (' + ', '.join(['%s'] * len(params)) + ')'
        self.execute(query, params)
        self.commit()

    def remove_check_in(self, class_id, user_id, class_date, class_time, child_id=None):
        conditions = ['user_id', 'class_id', 'class_date', 'class_time']
        params = [user_id, class_id, class_date, class_time]
        
        if child_id and not isnan(child_id):
            conditions.append('child_id')
            params.append(child_id)

        condition_string = ' = %s AND '.join(conditions) + ' = %s'
        query = 'DELETE FROM attendance WHERE ' + condition_string

        self.execute(query, params)
        self.commit()

    def get_attendance(self, from_date='', to_date='', user_id=None, class_id=None, 
                       columns=('classes.class_name', 'DATE_FORMAT(class_time, "%H:%i") class_time', 'class_date', 'class_id', 'user_id',
                                'membership_type', 'date AS check_in_time', 'child_id'),
                       extra_columns=None):

        full_name_col = '''CASE 
                                WHEN child_id > 0 THEN CONCAT(children.first_name, " ", children.last_name)
                                    ELSE CONCAT(users.first_name, " ", users.last_name)
                            END AS full_name'''

        all_columns = list(columns)
        all_columns.append(full_name_col)
        query_columns = ', '.join(all_columns)

        if extra_columns:
            query_columns += ', ' + ', '.join(extra_columns)
        query = f'SELECT {query_columns}  FROM attendance '
        query += 'INNER JOIN classes ON attendance.class_id=classes.id INNER JOIN users ON attendance.user_id=users.id ' 
        query += 'INNER JOIN memberships ON memberships.id=users.membership_id '
        query += 'LEFT JOIN children ON child_id=children.id'
        where_clause = ' WHERE '
        conditions = []
        params = []
        print(query)
        if from_date:
            conditions.append('date >= %s')
            params.append(from_date)
        if to_date:
            conditions.append('date <= %s')
            params.append(to_date)

        if user_id:
            conditions.append('user_id = %s')
            params.append(user_id)
        if class_id:
            conditions.append('class_id = %s')
            params.append(class_id)

        where_clause += ' AND '.join(conditions)
        if conditions:
            query += where_clause
        self.execute(query, params)
        return self.cursor.fetchall()

    def get_absentees(self, from_date=''):
        if not from_date:
            from_date = datetime.today() - timedelta(days=14)

        query = 'SELECT DISTINCT CONCAT(users.first_name, " ", users.last_name) AS full_name, users.email, users.mobile_number, '
        query += 'DATE_FORMAT(a1.date, "%a %d/%m/%Y") last_class '
        query += 'FROM attendance a1 RIGHT JOIN users ON a1.user_id=users.id WHERE users.is_coach = false AND'
        query += '((a1.date = (SELECT MAX(a2.date) FROM attendance a2 WHERE a2.user_id=a1.user_id) AND a1.date <= %s) OR a1.date IS NULL)'
        params = (from_date.date(),)
        self.execute(query, params)
        return self.cursor.fetchall()

    def get_membership_types(self, extra_cols=[]):
        query = 'SELECT memberships.id, membership_type, age_groups.name FROM memberships JOIN age_groups ON age_group_id=age_groups.id'
        self.execute(query)
        return self.cursor.fetchall()

    def add_membership(self, name, age_group_id, sessions_per_week):
        query = 'INSERT INTO memberships (membership_type, age_group_id, sessions_per_week) VALUES (%s, %s, %s)'
        params = [name, age_group_id, sessions_per_week]
        self.execute(query, params)
        self.commit()
    
    def get_age_groups(self):
        query = 'SELECT id, name FROM age_groups'
        self.execute(query)
        return self.cursor.fetchall()

    def update_unlimited_class_count(self):
        query = 'UPDATE memberships SET sessions_per_week = (SELECT COUNT(id) FROM classes) WHERE membership_type = "unlimited"'
        self.execute(query)
        return self.commit()

    def add_password_reset(self, uid, token):
        query = 'INSERT INTO password_resets (user_id, token, valid_until) VALUES (%s, %s, %s)'
        valid_until = (datetime.today() + timedelta(days=1))
        params = (uid, token, valid_until)
        self.execute(query, params)
        self.commit()

    def validate_password_reset(self, token):
        query = 'SELECT user_id, valid_until FROM password_resets WHERE token=%s'
        params = (token,)
        self.execute(query, params)
        result = self.cursor.fetchone()

        if result and datetime.today() < result.get('valid_until'):
            return True, result.get('user_id')
        
        return False, 0

    def remove_password_reset_token(self, token):
        query = 'DELETE FROM password_resets WHERE token=%s'
        params = (token,)
        self.execute(query, params)
        self.commit()


class QueryResult(DataFrame):
    def __bool__(self):
        return not self.empty


def get_end_of_day(day: datetime) -> datetime:
    return day.replace(hour=0, minute=0, second=0) + timedelta(days=1)


def order_query(params, order, descending):
    if order:
        q = ' ORDER BY %s DESC' if descending else ' ORDER BY %s'
        params.append(order)
    else:
        q = ''
    
    return q


def select(columns, table):
    return 'SELECT ' + ', '.join(columns) + ' FROM ' + table


def save_files(challenge_id, files, file_purpose, parent_folder, uid, file_name=None):
    params = []
    for f in files:
        if f.filename:
            file_name = file_name if file_name else f.filename
            path = get_file_path(challenge_id, file_purpose, file_name, parent_folder)
            f.save(path)
            params.append([challenge_id, file_purpose, basename(path), uid])
            file_name = None

    return params


def get_file_path(challenge_id, purpose, file_name, parent_folder, make_folders=True):
    path = os.path.join(os.path.abspath(current_app.instance_path), parent_folder, str(challenge_id), purpose)
    path = os.path.join(path, secure_filename(str(file_name)))
    if make_folders:
        return make_folder(path)
    return path


# TODO: build filename dynamically
def get_file_name(sub_path):
    instance_path = current_app.instance_path
    filename = secure_filename(basename(sub_path))
    sub_path = os.path.join(dirname(sub_path), filename)
    save_path = make_folder(os.path.join(instance_path, sub_path))
    return save_path


def make_folder(path):
    try:
        os.makedirs(dirname(path))
    except OSError:
        print(f'Could not make path {path}')
    return path


def get_db():
    if 'db' not in g:
        g.db = Database()

    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


@click.command('init-db')
@with_appcontext
def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

    click.echo('Initialised the database.')


@click.command('update-db')
@click.argument('filename')
@with_appcontext
def update_db(filename):
    db = get_db()

    with open(filename) as f:
        db.executescript(f.read())

    click.echo(f'Updated the DB with script: {filename}')


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db)
    app.cli.add_command(update_db)
