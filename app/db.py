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


class Database:
    def __init__(self, db_name='wuxia', db_host=None, db_user=None, db_pass=None):
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
        params = ('wuxia',)
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

    def get_users(self, columns=('*',)):
        self.execute(select(columns, 'users'))
        users = self.cursor.fetchall()
        return users

    def get_user(self, uid=None, name=None, columns=('*',)):
        query = select(columns, 'users') + ' WHERE '
        params = tuple()

        if uid:
            query += 'id = %s'
            params = (uid,)
        elif name:
            query += 'username = %s'
            params = (name,)
        else:
            try:
                current_user_id = g.user['id']
                query += 'id = %s'
                params = (current_user_id,)
            except RuntimeError:
                return params

        self.execute(query, params)
        return self.cursor.fetchone()

    def add_user(self, username, password, admin_level='no'):
        query = 'INSERT INTO users (username, password, admin) VALUES (%s, %s, %s)'
        params = (username, generate_password_hash(password), admin_level)
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

    def set_story_access(self, uid, access=True):
        query = 'UPDATE users SET access_approved = %s WHERE id = %s'
        params = (int(access), uid)
        self.execute(query, params)
        self.commit()

    def add_challenge(self, title, short_description, long_description, verification_file_name, verifiers,
                      expected_results, samples=None):
        query = 'INSERT INTO challenges (title, short_description, verifier_filename) VALUES (%s, %s, %s)'
        params = (title, short_description, verification_file_name)
        self.execute(query, params)
        self.commit()
        challenge_id = self.cursor.lastrowid
        
        self.add_challenge_description(challenge_id, long_description.splitlines())
        self.add_challenge_files(challenge_id, verifiers, expected_results, samples)
        self.commit()
        return challenge_id

    def add_challenge_description(self, challenge_id, description=(None,)):
        query = 'INSERT INTO challenge_descriptions (challenge_id, sequence_num, description) VALUES (%s, %s, %s)'
        params = [(challenge_id, idx, paragraph) for idx, paragraph in enumerate(description)]
        self.executemany(query, params)

    def add_challenge_files(self, challenge_id, verifiers, expected_results, samples=None):
        query = 'INSERT INTO challenge_files (challenge_id, type, file_name, user_id) VALUES (%s, %s, %s, %s)'
        params = save_files(challenge_id, verifiers, 'verifier', self.challenge_parent_folder, g.user['id'])
        params.extend(save_files(challenge_id, expected_results, 'result', self.challenge_parent_folder, g.user['id']))
        if samples:
            params.extend(save_files(challenge_id, samples, 'sample', self.challenge_parent_folder, g.user['id']))

        self.executemany(query, params)

    def add_challenge_file(self, new_file, challenge_id, file_type, file_name, user_id):
        # Check whether user code file already exists
        if user_id and self.get_challenge_files(challenge_id, user_id, ['user']):
            return save_files(challenge_id, [new_file], file_type, self.challenge_parent_folder, user_id, file_name)[0]
        else:
            query = 'INSERT INTO challenge_files (challenge_id, type, file_name, user_id)'
            query += ' VALUES (%s, %s, %s, %s)'
            params = save_files(challenge_id, [new_file], file_type, self.challenge_parent_folder, user_id, file_name)[0]
            self.execute(query, params)
            self.commit()

    def get_challenges(self, challenge_id=None, columns=('*',), order_by=None, descending=False):
        query = select(columns, 'challenges')
        params = []
        if challenge_id:
            query += ' WHERE id = %s'
            params.append(challenge_id)

        query += order_query(params, order_by, descending)
        self.execute(query, params)
        return self.cursor.fetchall()

    def get_challenge_description(self, challenge_id, columns=('*',), order_by=None, descending=False):
        query = select(columns, 'challenge_descriptions') + ' WHERE challenge_id = %s'
        params = [challenge_id]
        query += order_query(params, order_by, descending)
        self.execute(query, params)
        return self.cursor.fetchall()

    def get_challenge_files(self, challenge_id, user_id=None, file_types=None, columns=('*',)):
        query = select(columns, 'challenge_files') + ' WHERE challenge_id = %s'
        params = [challenge_id]

        if file_types:
            query += ' AND (' + ('type = %s OR' * len(file_types))[:-3] + ')'
            params.extend(file_types)
        if user_id:
            query += ' AND user_id = %s'
            params.append(user_id)

        self.execute(query, params)
        return self.cursor.fetchall()

    def get_challenge_file_urls(self, challenge_id, file_types=None, url_prefix='/challenges/files'):
        files = self.get_challenge_files(challenge_id, file_types=file_types, columns=('type', 'file_name'))
        urls = [os.path.join(url_prefix, str(challenge_id), f['type'], f['file_name']) for f in files]
        return urls

    def delete_challenge(self, challenge_id):
        query = 'DELETE FROM challenges WHERE id = %s'
        params = [challenge_id]
        self.execute(query, params)
        self.delete_challenge_files(challenge_id)
        self.delete_challenge_description(challenge_id)
        self.commit()
        flash(f'Deleted challenge {challenge_id} from database.')
        # Remove challenge files from file system
        try:
            challenge_id = int(challenge_id)
            challenge_folder = os.path.join(current_app.instance_path, self.challenge_parent_folder, str(challenge_id))
            rmtree(challenge_folder)
            flash(f'Deleted files for challenge {challenge_id}.')
        except ValueError:
            flash(f'Could not delete files for challenge {challenge_id}.')
        except FileNotFoundError:
            pass

    def delete_challenge_description(self, challenge_id, seq=None, commit=False):
        query = 'DELETE FROM challenge_descriptions WHERE challenge_id = %s'
        params = [challenge_id]
        if seq:
            query += ' AND sequence_num = %s'
            params.append(seq)

        self.execute(query, params)
        if commit:
            self.commit()

    def delete_challenge_files(self, challenge_id, file_types=None, user_id=None, commit=False):
        query = 'DELETE FROM challenge_files WHERE challenge_id = %s'
        params = [challenge_id]
        if file_types:
            query += ' AND (' + ('type = %s OR' * len(file_types))[:-3] + ')'
            params.extend(file_types)
        if user_id:
            query += ' AND user_id = %s'
            params.append(user_id)

        self.execute(query, params)
        if commit:
            self.commit()

    def get_stories(self):
        query = 'SELECT stories.*, (SELECT COUNT(chapters.id) FROM chapters WHERE story_id = stories.id'
        query += ') chapter_count, users.username FROM stories INNER JOIN users ON stories.uploader_id=users.id'
        #query = 'SELECT * FROM stories'
        self.execute(query)
        return self.cursor.fetchall()

    def get_story(self, story_id, columns=('*',)):
        query = f'SELECT {",".join(columns)} FROM stories WHERE id = %s'
        params = (story_id,)
        self.execute(query, params)
        return self.cursor.fetchone()

    def check_story(self, title, author):
        query = 'SELECT id FROM stories WHERE title = %s AND author = %s'
        params = (title, author)
        self.execute(query, params)
        return self.cursor.fetchone()
    
    def get_chapters(self, story_id, columns=('*',)):
        query = f'SELECT {",".join(columns)} FROM chapters WHERE story_id = %s'
        params = (story_id,)
        self.execute(query, params)
        return self.cursor.fetchall()

    def add_story(self, title, author, uploader):
        query = 'INSERT INTO stories (title, author, uploader_id) VALUES (%s,%s,%s)'
        params = (title, author, uploader)
        self.execute(query, params)
        self.commit()

    def add_chapter(self, story_id, chapter_title, chapter_content, chapter_num,
                    uploader_id, commit=True):
        query = 'INSERT INTO chapters (story_id, chapter_number, chapter_title, \
                chapter_content, uploader_id) VALUES (%s, %s, %s, %s, %s)'
        params = (int(story_id), chapter_num, chapter_title, chapter_content,
                  uploader_id)
        self.execute(query, params)
        if commit:
            self.commit()

    def delete_story(self, story_id):
        self.delete_chapters(story_id)
        query = 'DELETE FROM stories WHERE id = %s'
        params = (story_id,)
        self.execute(query, params)
        self.commit()

    def delete_chapters(self, story_id):
        query = 'DELETE FROM chapters WHERE story_id = %s'
        params = (story_id,)
        self.execute(query, params)
        self.commit()

    def get_coaches(self):
        query = 'SELECT id, username FROM users WHERE is_coach=true'
        self.execute(query)
        return self.cursor.fetchall()

    def add_class(self, class_name, weekday, time, duration, coach_id, class_type='No Gi'):
        if class_type not in ['Gi', 'No Gi']:
            flash('Invalid class type. Class type must be either Gi or No Gi')
            return False

        query = 'INSERT INTO classes (class_name, class_type, weekday, time, duration, coach_id) '
        query += 'VALUES (%s, %s, %s, %s, %s, %s)'
        params = (class_name, class_type, weekday, time, duration, coach_id)
        self.execute(query, params)
        self.commit()
        return True

    def get_classes(self, weekday=None, class_time=None):
        query = 'SELECT id, DATE_FORMAT(time, "%H:%i") class_time, class_name, duration, '
        query += 'DATE_FORMAT(ADDTIME(time, duration), "%H:%i") end_time, weekday'
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

        possible_previous_class_time = time.fromisoformat(show_classes_from_time)
        params.append(possible_previous_class_time.isoformat())

        self.execute(query, params)
        todays_classes = self.cursor.fetchall()
        return todays_classes

    def get_all_classes(self):
        query = 'SELECT id, DATE_FORMAT(time, "%H:%i") class_time, class_name, duration, '
        query += 'DATE_FORMAT(ADDTIME(time, duration), "%H:%i") end_time, weekday'
        query += ' FROM classes'
        self.execute(query)
        return self.cursor.fetchall()


    def check_in(self, class_id, user_id, class_date, class_time):
        query = 'INSERT INTO attendance (user_id, class_id, class_date, class_time) VALUES (%s, %s, %s, %s);'
        params = (user_id, class_id, class_date, class_time)
        self.execute(query, params)
        self.commit()

    def get_attendance(self, from_date, to_date, user_id=None, class_id=None):
        query = 'SELECT date, class_id, classes.class_name, class_date, DATE_FORMAT(class_time, "%H:%i") class_time, '
        query += 'classes.class_type, users.username FROM attendance '
        query += 'INNER JOIN classes ON attendance.class_id=classes.id INNER JOIN users ON attendance.user_id=users.id'
        query += ' WHERE date >= %s AND date <= %s'
        params = [from_date, to_date]

        if user_id:
            query += ' AND user_id = %s'
            params.append(user_id)
        if class_id:
            query += ' AND class_id = %s'
            params.append(class_id)

        print(query, params)
        self.execute(query, params)
        return self.cursor.fetchall()


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
