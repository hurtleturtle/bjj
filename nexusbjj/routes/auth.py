import functools
from flask import Blueprint, flash, g, render_template, request, session
from flask import url_for, redirect, escape, make_response
from werkzeug.security import check_password_hash, generate_password_hash
from nexusbjj.db import get_db
from nexusbjj.forms import gen_form_item
from datetime import datetime, timedelta


bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = escape(request.form['username'])
        password = escape(request.form['password'])
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif db.get_user(name=username) is not None:
            error = f'User {username} is already registered.'

        if error is None:
            db.add_user(username, password)
            return login()

        flash(error)

    return render_template('auth/register.html',
                           form_groups=get_user_form('register'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    status_code = 200
    referrer = request.args.get('next')

    if request.method == 'POST':
        username = escape(request.form['username'])
        password = escape(request.form['password'])
        db = get_db()
        error = None
        user = db.get_user(name=username)

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            url = referrer if referrer else url_for('story.story_list')
            response = make_response(redirect(url))
            expiry = datetime.now() + timedelta(minutes=60)
            response.set_cookie('test-cookie', value='this_cookie_expires_at_' + str(expiry), expires=expiry)
            return response

        if error:
            flash(error)
            status_code = 401

    return render_template('auth/login.html',
                           form_groups=get_user_form('login')), status_code


@bp.route('/logout')
def logout():
    session.clear()
    response = make_response(redirect(url_for('index')))
    response.delete_cookie('pirate')
    return response


def get_user_form(form_type):
    groups = {
        'user': {
            'group_title': form_type.capitalize(),
            'username': gen_form_item('username', placeholder='Username',
                                      required=True),
            'password': gen_form_item('password', placeholder='Password',
                                      required=True, item_type='password')
        },
        'submit': {
            'button': gen_form_item('btn-submit', item_type='submit',
                                    value=form_type.capitalize())
        },
    }
    return groups


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().get_user(uid=user_id)


@bp.before_app_request
def load_admin_levels():
    g.admin_levels = ['read', 'read-write']
    g.privilege_levels = ['no', 'test'] + g.admin_levels


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect_to_referrer()

        return view(**kwargs)

    return wrapped_view


def approval_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        error = None

        if g.user is None:
            return redirect_to_referrer()
        if not g.user['access_approved']:
            error = f'You do not have access to {request.url}. Please contact '
            error += 'support.'

        if error:
            flash(error)
            return redirect(url_for('index'))

        return view(**kwargs)

    return wrapped_view


def test_access_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not g.user:
            flash('Please login to access that page.')
            return redirect_to_referrer()
        elif g.user['admin'] == 'no':
            flash('You do not have sufficient privileges to access that page.')
            return redirect(url_for('index'))
        
        return view(**kwargs)
    return wrapped_view


def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        error = None
        url = None

        if g.user is None:
            flash('Please login to access that page.')
            return redirect_to_referrer()
        elif g.user['admin'] not in g.admin_levels:
            url = 'index'
            error = 'You must have admin privileges to access that page.'
            
        if error:
            flash(error)
            return redirect(url_for(url))

        return view(**kwargs)

    return wrapped_view


def write_admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('Please login to access that page.')
            return redirect_to_referrer()
        if g.user['admin'] != 'read-write':
            flash('Write access required')
            return redirect(url_for('index'))

        return view(**kwargs)

    return wrapped_view


def redirect_to_referrer(url='auth.login', **kwargs):
    referrer = request.full_path
    return redirect(url_for(url, next=referrer, **kwargs))


@bp.before_app_request
def update_access_time():
    if g.user is not None:
        db = get_db()
        db.update_user_access_time(g.user['id'])
