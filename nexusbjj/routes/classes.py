from flask import Blueprint, request, render_template, flash, g
from nexusbjj.routes.auth import admin_required, login_required
from nexusbjj.forms import gen_form_item, gen_options
from nexusbjj.db import get_db, QueryResult
from datetime import datetime, time, timedelta
from calendar import day_name
from pandas import Categorical, concat, DataFrame
from numpy import nan, float64, isnan


bp = Blueprint('classes', __name__, url_prefix='/classes', template_folder='templates/classes')


@bp.route('/check-in', methods=['GET'])
@login_required
def check_in_to_class():
    db = get_db()
    current_user = db.get_user(columns=('id', 'first_name', 'last_name', 'parent_id'))
    children = QueryResult(db.get_children(current_user['id']))
    today = datetime.today()
    today_start = datetime.combine(today.date(), time.fromisoformat('00:00:00')).isoformat()
    today_end = datetime.combine(today.date(), time.fromisoformat('23:59:59')).isoformat()
    current_user_attendance = QueryResult(db.get_attendance(from_date=today_start, to_date=today_end,
                                          user_id=current_user['id']))
    age_groups = QueryResult(db.get_age_groups())
    age_group_id = current_user['age_group_id']
    child_id = request.args.get('child_id')
    NOT_A_CHILD = -1
    
    if child_id:
        child_id = int(child_id)
    
    request_class_id = request.args.get('class_id')
    child_age_group_id = age_groups.set_index('name').loc['junior', 'id']

    if current_user['age_group'] == 'family':
        age_group_id = int(age_groups.set_index('name').loc['senior', 'id'])
        current_user['age_group_id'] = age_group_id

        if children:
            children['age_group_id'] = child_age_group_id
            children.rename(columns={'id': 'child_id'}, inplace=True)
            children['id'] = current_user['id']

    users = concat([QueryResult([current_user]), children], axis='index', ignore_index=True)

    try:
        if users['child_id'].empty:
            users['child_id'] = nan
    except KeyError:
        users['child_id'] = nan
    
    classes = QueryResult(db.get_all_classes(conditions='weekday = %s', params=[today.strftime('%A')]))

    if not classes:
        flash('No classes available')
        return render_template('checkin.html')
    
    classes.sort_values(by=['class_time'], inplace=True)
    df_classes = check_attendance(users, classes, current_user_attendance)
    df_classes['class_date'] = today.date().isoformat()

    if request_class_id:
        toggle_check_in(df_classes, request_class_id, current_user['id'], child_id)

    flag_all_classes_attended = all(df_classes['attendance'])
    df_classes['child_id'] = df_classes['child_id'].fillna(NOT_A_CHILD).astype(int)

    classes_by_user = []
    for index, user in users.iterrows():
        user_classes = {
            'index': index,
            'name': user['first_name'] + ' ' + user['last_name']
        }

        if not isnan(user['child_id']):
            user_classes['child_id'] = int(user['child_id'])
            mask = df_classes['child_id'] == int(user['child_id'])
        else:
            mask = df_classes['child_id'] == NOT_A_CHILD
        
        user_classes['classes'] = df_classes.loc[mask]

        if not user_classes['classes'].empty:
            classes_by_user.append(user_classes)

    return render_template('checkin.html', classes=df_classes.to_dict('records'), user_classes=classes_by_user, 
                           all_classes_attended=flag_all_classes_attended, children=children)


def check_attendance(users: QueryResult, classes: QueryResult, attendance: QueryResult) -> QueryResult:
    total_attendance = DataFrame()

    for index, user in users.iterrows():
        user_classes = classes[classes['age_group_id'] == user['age_group_id']].copy()
        user_classes['user_id'] = user['id']
        user_classes['child_id'] = user['child_id']
        
        if attendance:
            attendance['child_id'] = attendance['child_id'].astype(float64)
            if isnan(user['child_id']):
                child_mask = attendance['child_id'].isnull()
            else:
                child_mask = attendance['child_id'] == user['child_id']
                
            user_classes['attendance'] = user_classes['id'].apply(lambda x: x in attendance.loc[child_mask, 'class_id'].values)
        else:
            user_classes['attendance'] = False
        
        total_attendance = concat([total_attendance, user_classes], ignore_index=True)
    
    return total_attendance


def toggle_check_in(df_classes: QueryResult, class_id, user_id, child_id=None):
    db = get_db()

    if not child_id:
        user_mask = (df_classes['user_id'] == user_id) & (df_classes['child_id'].isnull())
    else:
        user_mask = (df_classes['user_id'] == user_id) & (df_classes['child_id'] == child_id)
    df_classes.loc[:, 'check_in_function'] = 'no operation'

    if class_id == 'all':
        if all(df_classes['attendance']):
            df_classes['check_in_function'] = db.remove_check_in
            df_classes['attendance'] = False
        elif not any(df_classes['attendance']):
            df_classes['check_in_function'] = db.check_in
            df_classes['attendance'] = True
        else:
            mask = df_classes['attendance'] == False
            df_classes.loc[mask, 'check_in_function'] = db.check_in
            df_classes.loc[mask, 'attendance'] = True
    else:
        class_mask = df_classes['id'] == int(class_id)
        if df_classes.loc[user_mask & class_mask, 'attendance'].all():
            df_classes.loc[user_mask & class_mask, 'check_in_function'] = db.remove_check_in
            df_classes.loc[user_mask & class_mask, 'attendance'] = False
        else:
            df_classes.loc[user_mask & class_mask, 'check_in_function'] = db.check_in
            df_classes.loc[user_mask & class_mask, 'attendance'] = True

    for row in df_classes[df_classes['check_in_function'] != 'no operation'].itertuples():
        row.check_in_function(row.id, user_id, row.class_date, row.class_time, row.child_id)


@bp.route('/')
@login_required
def timetable():
    db = get_db()
    classes = QueryResult(db.get_all_classes())
    columns = ['weekday', 'class_name', 'class_time', 'end_time']

    if classes:
        classes = classes[columns].fillna(0)
        classes['weekday'] = Categorical(classes['weekday'], categories=list(day_name), ordered=True)
        classes.sort_values(['weekday', 'class_time'])
        classes['class_time'] = classes['class_time'].str.cat(classes['end_time'], sep='-')
        columns.remove('end_time')
        classes = classes[columns]
        classes.rename(columns={
            'class_name': 'Class',
            'weekday': 'Day',
            'class_time': 'Time'
        }, inplace=True)

    return render_template('classes.html', table_data=QueryResult(classes), table_title='Classes')


@bp.route('/add-class', methods=['GET', 'POST'])
@admin_required
def add_class():
    db = get_db()
    coaches = QueryResult(db.get_coaches())
    coaches['full_name'] = coaches['first_name'].str.cat(coaches['last_name'], sep=' ')
    age_groups = QueryResult(db.get_age_groups())
    default_age_group = age_groups.set_index('name').loc['senior', 'id']
    
    groups = {
        'class': {
            'group_title': 'Add Class',
            'class_name': gen_form_item('class_name', label='Class Name'),
            'class_age': gen_form_item('class_age_group', label='Age Group', field_type='select', 
                                       options=gen_options(age_groups['name'].str.capitalize().to_list(), 
                                       values=age_groups['id'].to_list()),
                                       selected_option=default_age_group),
            'class_type': gen_form_item('class_type', label='Class Type', field_type='select',
                                        options=gen_options(('No Gi', 'Gi'))),
            'class_coach': gen_form_item('class_coach', label='Coach', field_type='select',
                                         options=gen_options(coaches['full_name'].to_list(), 
                                         values=coaches['id'].to_list())),
            'class_day': gen_form_item('class_day', label='Day', field_type='select',
                                       options=gen_options(('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                                                            'Saturday', 'Sunday'))),
            'class_time': gen_form_item('class_time', label='Time (24h)', item_type='time'),
            'class_duration': gen_form_item('class_duration', label='Duration', item_type='time', value="01:00")
        },
        'submit': {
            'btn_submit': gen_form_item('btn-submit', item_type='submit', value='Submit')
        }
    }

    if request.method == 'POST':
        form = request.form
        class_name = form.get('class_name')
        class_type = form.get('class_type')
        class_coach_id = form.get('class_coach')
        class_day = form.get('class_day')
        class_time = form.get('class_time')
        class_duration = form.get('class_duration')
        class_age_group = form.get('class_age_group')

        db.add_class(class_name, class_day, class_time, class_duration, class_coach_id, class_age_group, class_type,)
        db.update_unlimited_class_count()

        flash('Class added!')


    return render_template('add_class.html', form_groups=groups)