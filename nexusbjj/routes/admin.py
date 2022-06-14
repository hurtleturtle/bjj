from flask import Blueprint, make_response, redirect, request, render_template, flash, url_for, g
from nexusbjj.routes.auth import admin_required, write_admin_required, login_required
from nexusbjj.forms import gen_form_item, gen_options
from nexusbjj.db import get_db, QueryResult
from datetime import datetime, timedelta
import pandas as pd
from calendar import day_name


bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates/admin')


@bp.route('/memberships', methods=['GET'])
@admin_required
def get_memberships():
    db = get_db()
    memberships = QueryResult(db.get_membership_types())
    return render_template('memberships.html', table_data=memberships, page_title='Memberships', table_title='Memberships',
                            add_func='admin.add_membership')


@bp.route('/memberships/add', methods=['GET', 'POST'])
@write_admin_required
def add_membership():
    db = get_db()
    age_groups = QueryResult(db.get_age_groups())
    groups = {
        'membership': {
            'group_title': 'Add Membership',
            'age': gen_form_item('age_group', label='Age Group', field_type='select', 
                                 options=gen_options(age_groups['name'].str.capitalize().values, age_groups['id'].values.tolist())),
            'sessions': gen_form_item('sessions_per_week', label='Sessions Per Week', item_type='number', value=0),
            'name': gen_form_item('name', label='Name')
        },
        'submit': {
            'btn-submit': gen_form_item('btn-submit', item_type='submit', value='Add')
        }
    }

    if request.method == 'POST':
        age_group = int(request.form.get('age_group'))
        sessions_per_week = int(request.form.get('sessions_per_week'))
        name = request.form.get('name').lower()

        db.add_membership(name, age_group, sessions_per_week)
        flash(f'Added membership: {name}')

        return redirect(url_for('admin.get_memberships'))

    return render_template('memberships.html', form_groups=groups)


@bp.route('/children')
@login_required
def list_children():
    db = get_db()
    user_id = g.user['id']
    children = QueryResult(db.get_children(user_id))

    if children:
        children['Name'] = children['first_name'].str.cat(children['last_name'], sep=' ')

        def get_membership_name(x):
            if x is None:
                return 'Unlimited'
            else:
                membership = db.get_membership(membership_id=x)
                return membership['membership_type'].capitalize()

        children['Membership'] = children['membership_id'].apply(get_membership_name)
        children = QueryResult(children[['Name', 'Membership']])

    title = 'Children'
    return render_template('children.html', table_data=children, table_title=title, page_title=title, add_func='admin.add_child')


@bp.route('/children/add', methods=['GET', 'POST'])
@login_required
def add_child():
    db = get_db()
    groups = {
        'child': {
            'group_title': 'Add Child',
            'first_name': gen_form_item('first_name', label='First Name', required=True),
            'last_name': gen_form_item('last_name', label='Last Name', required=True)
        },
        'submit': {
            'btn_submit': gen_form_item('btn-submit', item_type='submit', value='Add') 
        }
    }
    title='Add Child'
    parent_membership = db.get_membership(user_id=g.user['id'])

    if parent_membership['sessions_per_week'] == 0:
        junior_options = QueryResult(db.get_membership_types(conditions='age_groups.name=%s', params=['junior']))
        groups['child']['membership'] = gen_form_item('membership_id', label='Membership', required=True, field_type='select',
                                                      options=gen_options(junior_options['membership_type'].str.capitalize().to_list(),
                                                                          junior_options['id'].to_list()))

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        membership_id = request.form.get('membership_id', int(parent_membership.get('id')))
        db.add_child(first_name, last_name, g.user['id'], membership_id)

        parent_name = g.user['first_name'] + ' ' + g.user['last_name']
        flash(f'{first_name} {last_name} added as child of {parent_name}')
        return redirect(url_for('admin.list_children'))

    return render_template('children.html', form_groups=groups, table_title=title, page_title=title, add_func='admin.add_child')