import functools
from flask import Blueprint, flash, g, render_template, request, session
from flask import url_for, redirect, escape, current_app, make_response
from werkzeug.security import check_password_hash, generate_password_hash
from nexusbjj.db import get_db, QueryResult
from nexusbjj.forms import gen_form_item, gen_options
from datetime import datetime, timedelta
from secrets import token_urlsafe
from nexusbjj.email import Email
import jwt
from jwt.exceptions import InvalidSignatureError, DecodeError


bp = Blueprint('auth', __name__, url_prefix='/auth', template_folder='templates/auth')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = escape(request.form['email'])
        password = escape(request.form['password'])
        confirm_password = escape(request.form['confirm_password'])
        first_name = escape(request.form['first_name'])
        last_name = escape(request.form['last_name'])
        mobile = escape(request.form['mobile'])
        membership_type = escape(request.form['membership_type'])
        db = get_db()
        error = None

        if db.get_user(email=email) is not None:
            error = f'User {email} is already registered.'

        if error is None:
            if confirm_password == password:
                db.add_user(email, password, first_name, last_name, mobile, membership_type)
                return login(True)
            else:
                error = 'Your passwords did not match. Please try again.'
                flash(error)
                args = (email, first_name, last_name, mobile, membership_type)
                return render_template('register.html', form_groups=get_registration_form(*args))

        flash(error)

    return render_template('register.html', form_groups=get_registration_form())


def get_registration_form(email='', first_name='', last_name='', mobile='', membership_id=''):
    db = get_db()
    memberships = QueryResult(db.get_membership_types())
    membership_types = (memberships['name'].str.capitalize() + ' - ' + memberships['membership_type'].str.capitalize()).tolist()
    groups = {
        'user': {
            'group_title': 'Register',
            'first_name': gen_form_item('first_name', label='First Name', placeholder='Required', required=True,
                                        value=first_name),
            'last_name': gen_form_item('last_name', label='Surname', placeholder='Required', required=True,
                                       value=last_name),
            'mobile': gen_form_item('mobile', label='Mobile Number', placeholder='Required', required=True,
                                    value=mobile),
            'email': gen_form_item('email', label='Email', value=email,
                                      required=True, placeholder='Required', item_type='email'),
            'membership': gen_form_item('membership_type', label='Membership Type', field_type='select',
                                        options=gen_options(membership_types, 
                                                            values=memberships['id'].values.tolist()), 
                                        selected_option=membership_id),
            'password': gen_form_item('password', label='Password', placeholder='Required',
                                      required=True, item_type='password'),
            'confirm_password': gen_form_item('confirm_password', label='Confirm Password', required=True,
                                              placeholder='Required', item_type='password')
        },
        'submit': {
            'button': gen_form_item('btn-submit', item_type='submit',
                                    value='Register')
        },
    }
    return groups


@bp.route('/login', methods=['GET', 'POST'])
def login(check_in=True):
    status_code = 200
    referrer = request.args.get('next')
    db = get_db()
    user = db.get_user()

    if user:
        if user.get('is_coach'):
            return redirect(url_for('reports.headcount'))
        else:
            return redirect(url_for('classes.check_in_to_class'))

    if request.method == 'POST':
        email = escape(request.form['email'])
        password = escape(request.form['password'])
        error = None
        user = db.get_user(email=email)

        if user is None:
            error = 'Incorrect email or password.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect email or password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session.permanent = True

            if user.get('is_coach'):
                url = referrer if referrer else url_for('reports.headcount')
            elif check_in:
                url = referrer if referrer else url_for('classes.check_in_to_class')
            else:
                url = referrer if referrer else url_for('index')
            
            return redirect(url)

        if error:
            flash(error)
            status_code = 401

    return render_template('login.html', form_groups=get_user_form()), status_code


def get_user_form():
    groups = {
        'user': {
            'group_title': 'Login',
            'email': gen_form_item('email', label='Email', required=True, item_type='email'),
            'password': gen_form_item('password', label='Password', required=True, item_type='password'),
        },
        'submit': {
            'button': gen_form_item('btn-submit', item_type='submit',
                                    value='Login')
        },
        'reset': {
            'password-reset': gen_form_item('reset_password', href=url_for('auth.initiate_password_reset'), value='Forgotten Password?',
                                            field_type='link', field_class='mx-auto', item_class='centred-link small')
        },
        'register': {
            'break': True,
            'register_button': gen_form_item('register', href=url_for('auth.register'), field_type='link', field_class='link-button mx-auto',
                                             value='Create Account', item_class='centred-link mx-auto')
        }
    }
    return groups


@bp.route('/reset-password')
def initiate_password_reset():
    db = get_db()
    token = request.args.get('token')
    groups = {
        'user': {
            'group_title': 'Reset Password',
            'email': gen_form_item('email', label='Email', required=True, item_type='email', placeholder='Enter your email address')
        },
        'submit': {
            'button': gen_form_item('btn-submit', item_type='submit', value='Send Reset Email')
        }
    }

    if g.user:
        flash('You are already logged in. Please change your password here.')
        return redirect(url_for('users.change_password', uid=g.user['id']))

    if token:
        valid_token, user_id = db.validate_password_reset(token)
        if valid_token:
            return render_template('reset.html', form_groups=get_password_form_groups())  
        else:
            flash('Your token has expired. Please begin the password reset process again.')
            return redirect(url_for('auth.initiate_password_reset'))  

    return render_template('reset.html', form_groups=groups)


def get_password_form_groups():
    groups = {
        'passwd': {
            'group_title': 'Reset Password',
            'password': gen_form_item('password', placeholder='New password', item_type='password', required=True, item_class='py-1'),
            'confirm': gen_form_item('confirm', placeholder='Confirm password', item_type='password', required=True, item_class='py-1')
        },
        'submit': {
            'button': gen_form_item('btn_submit', item_type='submit', value='Reset Password')
        }
    }
    return groups


@bp.route('/reset-password', methods=['POST'])
def reset_password_for_user():
    token = request.args.get('token')
    db = get_db()

    if token:
        valid_token, user_id = db.validate_password_reset(token)
        if valid_token:
            password = request.form.get('password')
            confirm_password = request.form.get('confirm')

            if password == confirm_password:
                db.change_password(user_id, password)
                db.remove_password_reset_token(token)
                flash('Password updated!')
                return redirect(url_for('auth.login'))
            else:
                flash('Passwords do not match. Please try again.')
                return initiate_password_reset()
        else:
            flash('Your token has expired. Please begin the password reset process again.')
            return redirect(url_for('auth.initiate_password_reset'))
    else:
        email = request.form.get('email')
        generate_password_reset(email)

    return render_template('reset.html')


def generate_password_reset(email):
    db = get_db()
    user = db.get_user(email=email)

    if user:
        token = token_urlsafe(64)
        db.add_password_reset(user['id'], token)
        domain = 'https://members.warwickjudo.com'
        text_body = 'Please copy and paste the following link into your browser to reset your password: {}{}\n\nThe link is available for '
        text_body += '24 hours.'
        text_body = text_body.format(domain, url_for('auth.initiate_password_reset', token=token))
        email_body = render_template('reset_email.html', token=token, domain=domain)
        msg = Email(to=user['email'], text_body=text_body, html_body=email_body)
        msg.send_message()

    message = '<p>A password reset link has been emailed to the email address you entered, provided it is linked to an account.</p>'
    message += '<p>Please follow the steps in the email to reset your password (check your junk folder if the email does not appear in your '
    message += 'inbox).</p>'
    flash(message)


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


def set_user_token(user_id):
    user_jwt = jwt.encode(
        {'user_id': user_id},
        key=current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    return user_jwt

def get_user_from_token(token):
    if not token:
        print(g.user)
        return False

    try:
        user_id = jwt.decode(token, key=current_app.config['SECRET_KEY'], algorithms='HS256')['user_id']
    except InvalidSignatureError or DecodeError:
        return False
    
    return user_id


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


@bp.route('/login-as')
@write_admin_required
def login_as():
    user_id = int(request.args.get('user_id'))
    db = get_db()
    new_user = db.get_user(user_id)

    if new_user:
        session.clear()
        session['user_id'] = new_user['id']
        g.user = new_user
        return redirect(url_for('index'))
    
    return redirect(request.url)


def redirect_to_referrer(url='auth.login', **kwargs):
    referrer = request.full_path
    return redirect(url_for(url, next=referrer, **kwargs))


@bp.before_app_request
def update_access_time():
    if g.user is not None:
        db = get_db()
        db.update_user_access_time(g.user['id'])
