from flask import Blueprint, flash, g, render_template, request, url_for
from flask import redirect, escape, make_response
from werkzeug.security import check_password_hash, generate_password_hash
from nexusbjj.db import get_db, QueryResult
from nexusbjj.routes.auth import admin_required, write_admin_required, login_required
from nexusbjj.forms import gen_form_item, gen_options
from datetime import datetime


bp = Blueprint('users', __name__, url_prefix='/users')


@bp.route('')
@admin_required
def show_all():
    db = get_db()
    users = QueryResult(db.get_users()).drop('password', axis='columns')
    if request.args.get('export_to_csv'):
        filename = 'users' + datetime.today().date().isoformat() + '.csv'
        response = make_response(users.to_csv(index=False))
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=' + filename
        return response
    else:
        users['Name'] = users['first_name'].str.cat(users['last_name'], sep=' ')
        users = users.rename(columns={'membership_type': 'Membership'})
        users = QueryResult(users[['id', 'Name', 'Membership']])
    return render_template('users/list.html', table_data=users, table_title='Users', to_csv=True)


@bp.route('/<int:uid>/edit', methods=['GET', 'POST'])
@admin_required
def edit(uid):
    db = get_db()
    user = db.get_user(uid)
    admin_levels = g.privilege_levels

    if request.method == 'POST' and g.user['admin'] == 'read-write':
        error = None
        email = escape(request.form['email'])
        admin = request.form['admin']
        is_coach = request.form['is_coach']
        membership_id = request.form['membership']
        email_new = (email != user['email'])
        email_exists = db.get_user(email=email) is not None

        if email_new:
            if email_exists:
                error = 'Email exists'
            else:
                db.update_user(uid, 'email', email)
        if admin in admin_levels:
            db.update_user(uid, 'admin', admin)
        if is_coach is not None:
            db.update_user(uid, 'is_coach', is_coach)
        if membership_id != user['membership_id']:
            db.update_user(uid, 'membership_id', membership_id)
        else:
            error = error + '\n' if error else ''
            error += f'{admin}\nAdmin Status must be one of:'
            error += ' {}'.format(', '.join(admin_levels))

        if error:
            flash(error)
        else:
            return redirect(url_for('users.show_all'))
    elif request.method == 'POST' and g.user['admin'] != 'read-write':
        flash('Write access required')

    groups = generate_form_groups(user)
    return render_template('users/edit.html', form_groups=groups)


@bp.route('/<int:uid>/change-password', methods=['GET', 'POST'])
def change_password(uid):
    db = get_db()
    user = db.get_user(uid)

    if (not g.user or g.user['id'] != uid) and g.user['admin'] != 'read-write':
        error = 'Could not change password for the specified user.'
        flash(error)
        return redirect(url_for('index'))

    if request.method == 'POST':
        error = None
        old_pass = escape(request.form['old_pass'])
        new_pass = escape(request.form['new_pass'])
        confirm_pass = escape(request.form['confirm_pass'])

        if new_pass != confirm_pass:
            error = 'Passwords do not match.'

        if not check_password_hash(user['password'], old_pass) and \
        g.user['admin'] != 'read-write':
            error = 'Existing password incorrect.'

        if error:
            flash(error)
            return redirect(url_for('users.change_password', uid=uid))

        db.update_user(uid, 'password', generate_password_hash(new_pass))

        flash('Password updated.')
        return redirect(url_for('index'))

    groups = gen_pass_groups(user)
    return render_template('users/edit.html', form_groups=groups)


@bp.route('/<int:uid>/delete', methods=['GET', 'POST'])
@write_admin_required
def delete(uid):
    db = get_db()
    db.delete_user(uid)
    return redirect(url_for('users.show_all'))


@bp.route('/toggle-coach')
@write_admin_required
def toggle_coach():
    user_id = int(request.args.get('user_id'))
    db = get_db()
    user = db.get_user(uid=user_id, columns=('is_coach',))

    if user:
        db.update_user(user_id, 'is_coach', not user.get('is_coach'))
        flash('User updated successfully')
    else:
        flash('User not updated')

    return redirect(url_for('users.show_all'))


@bp.route('/<int:uid>/clear-session')
@write_admin_required
def clear_session(uid):
    db = get_db()

def get_current_user_id(default_uid=-1):
    try:
        user = g.user['id']
    except RuntimeError:
        user = default_uid
    
    return user


def generate_form_groups(user):
    password_href = url_for('users.change_password', uid=user['id'])
    delete_href = url_for('users.delete', uid=user['id'])
    db = get_db()
    memberships = QueryResult(db.get_membership_types())
    membership_types = list(memberships['name'].str.capitalize() + ' - ' + memberships['membership_type'].str.capitalize())
    membership_ids = list(memberships['id'])

    groups = {
        'user': {
            'group_title': 'Edit: {}'.format(user['email']),
            'email': gen_form_item('email', value=user['email'],
                                      required=True, label='Email'),
            'admin': gen_form_item('admin', required=True, label='Admin',
                                   field_type='select',
                                   options=gen_options(g.privilege_levels,
                                                       g.privilege_levels),
                                   value=user['admin'],
                                   selected_option=user['admin']),
            'coach': gen_form_item('is_coach', label='Coach', field_type='select',
                                   options=gen_options(['No', 'Yes'], [0, 1]),
                                   selected_option=user['is_coach']),
            'membership': gen_form_item('membership', label='Membership', field_type='select',
                                        options=gen_options(membership_types, membership_ids),
                                        selected_option=user['membership_id'])
        },
        'change_pass': {
            'button': gen_form_item('change_pass', field_type='link',
                                     href=password_href,
                                     value='Change Password')
        },
        'submit': {
            'button': gen_form_item('btn-submit', item_type='submit',
                                    value='Update', field_type='input')
        }
    }
    return groups


def gen_pass_groups(user):
    groups = {
        'user': {
            'group_title': 'Change Password for {}'.format(user['email']),
            'old_pass': gen_form_item('old_pass', label='Old Password',
                                      item_type='password', required=False),
            'new_pass': gen_form_item('new_pass', label='New Password',
                                      item_type='password', required=True),
            'confirm_pass': gen_form_item('confirm_pass', label='Confirm ' +
                                          'Password', item_type='password',
                                          required=True)
        },
        'submit': {
            'button': gen_form_item('btn-submit', item_type='submit',
                                    value='Change', field_type='input')
        }
    }
    return groups
