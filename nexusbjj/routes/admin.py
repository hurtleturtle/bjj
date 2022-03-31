from flask import Blueprint, make_response, redirect, request, render_template, flash, url_for, g
from nexusbjj.routes.auth import admin_required
from nexusbjj.forms import gen_form_item, gen_options
from nexusbjj.db import get_db, QueryResult
from datetime import datetime, timedelta
import pandas as pd
from calendar import day_name


bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates/admin')


@bp.route('/memberships', methods=['GET'])
def get_memberships():
    db = get_db()
    memberships = QueryResult(db.get_membership_types())
    return render_template('memberships.html', table_data=memberships, page_title='Memberships', table_title='Memberships',
                            add_func='admin.add_membership')


@bp.route('/memberships/add', methods=['GET', 'POST'])
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