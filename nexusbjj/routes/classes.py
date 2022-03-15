from flask import Blueprint, request, render_template, flash, g
from nexusbjj.routes.auth import admin_required, login_required
from nexusbjj.forms import gen_form_item, gen_options
from nexusbjj.db import get_db, QueryResult
from datetime import datetime, time
from calendar import day_name
from pandas import Categorical


bp = Blueprint('classes', __name__, url_prefix='/classes', template_folder='templates/classes')


@bp.route('/check-in', methods=['GET'])
@login_required
def check_in_to_class():
    db = get_db()
    current_user = db.get_user()
    today = datetime.today()
    today_start = datetime.combine(today.date(), time.fromisoformat('00:00:00')).isoformat()
    today_end = datetime.combine(today.date(), time.fromisoformat('23:59:59')).isoformat()
    current_user_attendance = QueryResult(db.get_attendance(from_date=today_start, to_date=today_end,
                                          user_id=current_user['id']))

    try:
        request_class_id = int(request.args.get('class_id'))
    except:
        request_class_id = request.args.get('class_id')
    classes = QueryResult(db.get_classes(age_group=current_user['age_group_id']))
    
    if not classes:
        flash('No classes available')
        return render_template('checkin.html')
    
    
    classes.sort_values(by=['class_time'], inplace=True)
    df_classes = check_attendance(classes.set_index('id'), current_user_attendance)
    df_classes['class_date'] = today.date().isoformat()

    if request_class_id:
        toggle_check_in(df_classes, request_class_id, current_user['id'])

    flag_all_classes_attended = all(df_classes['attendance'])
    
    return render_template('checkin.html', classes=df_classes.reset_index().to_dict('records'), 
                           all_classes_attended=flag_all_classes_attended)


def check_attendance(classes: QueryResult, user_attendance: QueryResult) -> QueryResult:
    if user_attendance:
        classes['attendance'] = classes.index.to_series().apply(lambda x: x in user_attendance['class_id'].values)
    else:
        classes['attendance'] = False
    return classes


def toggle_check_in(df_classes: QueryResult, class_id, user_id):
    db = get_db()
    df_classes['check_in_function'] = 'no operation'

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
        if df_classes.loc[class_id, 'attendance']:
            df_classes.loc[class_id, 'check_in_function'] = db.remove_check_in
            df_classes.loc[class_id, 'attendance'] = False
        else:
            df_classes.loc[class_id, 'check_in_function'] = db.check_in
            df_classes.loc[class_id, 'attendance'] = True

    for row in df_classes[df_classes['check_in_function'] != 'no operation'].itertuples():
        row.check_in_function(row.Index, user_id, row.class_date, row.class_time)


@bp.route('/')
@login_required
def show_classes():
    db = get_db()
    classes = QueryResult(db.get_all_classes())
    columns = ['class_name', 'weekday', 'class_time', 'end_time']

    if g.user['admin'] in g.admin_levels:
        attendance = QueryResult(db.get_attendance())
        if attendance:
            attendance = attendance.set_index('check_in_time').groupby('class_id')\
                                   .resample('1W-MON', label='left')['user_id'].count().unstack().fillna(0)
            attendance['avg_weekly_attendance'] = attendance.mean(axis='columns').round(2)
            attendance = QueryResult(attendance.reset_index()[['class_id', 'avg_weekly_attendance']])
            columns.append('avg_weekly_attendance')
    else:
        attendance = QueryResult(db.get_attendance(user_id=g.user['id']))
        columns.append('Attendances')
    
        if attendance:
            attendance = attendance[['class_id', 'user_id']].rename(columns={'user_id': 'Attendances'})
            attendance = QueryResult(attendance.groupby('class_id').count().reset_index())

    if attendance:        
        classes = QueryResult(classes.merge(attendance, on='class_id', how='left'))
    else:
        classes['Attendances'] = 0

    if classes:
        classes = classes[columns].fillna(0)
        classes['weekday'] = Categorical(classes['weekday'], categories=list(day_name), ordered=True)
        classes.sort_values(by=['weekday', 'class_time', 'class_name'], inplace=True)
        classes.rename(columns={
            'class_name': 'Class',
            'weekday': 'Day',
            'class_time': 'Start Time',
            'end_time': 'Finish Time'
        }, inplace=True)

        if g.user['admin'] not in g.admin_levels:
            classes['Attendances'] = classes['Attendances'].astype(int)
    return render_template('classes.html', table_data=QueryResult(classes), table_title='Classes')


@bp.route('/add-class', methods=['GET', 'POST'])
@admin_required
def add_class():
    db = get_db()
    coaches = QueryResult(db.get_coaches())
    coaches['full_name'] = coaches['first_name'].str.cat(coaches['last_name'], sep=' ')
    groups = {
        'class': {
            'group_title': 'Add Class',
            'class_name': gen_form_item('class_name', label='Class Name'),
            'class_type': gen_form_item('class_type', label='Class Type', field_type='select',
                                        options=gen_options(('No Gi', 'Gi')), value='No Gi',
                                        selected_option='No Gi'),
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

        db.add_class(class_name, class_day, class_time, class_duration, class_coach_id, class_type)
        db.update_unlimited_class_count()

        flash('Class added!')


    return render_template('add_class.html', form_groups=groups)