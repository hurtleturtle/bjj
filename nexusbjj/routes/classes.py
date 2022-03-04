from flask import Blueprint, request, render_template, flash, g
from nexusbjj.routes.auth import admin_required, login_required
from nexusbjj.forms import gen_form_item, gen_options
from nexusbjj.db import get_db, QueryResult
from datetime import datetime, time


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
    classes = db.get_classes()
    
    if not classes:
        return render_template('checkin.html')

    df_classes = check_attendance(QueryResult(classes).set_index('id'), current_user_attendance)

    if request_class_id == 'all':
        for class_id in df_classes.index:
            check_in_valid, error_message = validate_check_in(df_classes, class_id)
            if check_in_valid:
                db.check_in(class_id, current_user['id'], today.date().isoformat(), df_classes.loc[class_id, 'class_time'])
                df_classes.loc[class_id, 'attendance'] = True
            else:
                flash(error_message)
    elif request_class_id:
        check_in_valid, error_message = validate_check_in(df_classes, request_class_id)
        if check_in_valid:
            db.check_in(request_class_id, current_user['id'], today.date().isoformat(), df_classes.loc[request_class_id, 'class_time'])
            df_classes.loc[request_class_id, 'attendance'] = True
        else:
            flash(error_message)

    flag_all_classes_attended = all(df_classes['attendance'])
    
    return render_template('checkin.html', classes=df_classes.reset_index().to_dict('records'), 
                           all_classes_attended=flag_all_classes_attended)


def check_attendance(classes: QueryResult, user_attendance: QueryResult) -> QueryResult:
    if user_attendance:
        classes['attendance'] = classes.index.to_series().apply(lambda x: x in user_attendance['class_id'].values)
    else:
        classes['attendance'] = False
    return classes


def validate_check_in(df_classes: QueryResult, class_id: int):
    check_in_is_valid = True
    message = ''
    today = datetime.today()

    try:
        class_name = df_classes.loc[class_id, "class_name"]
        if df_classes.loc[class_id, 'attendance']:
            check_in_is_valid = False
            message = f'You have already checked in to {class_name}'
        
        if today.strftime('%A') != df_classes.loc[class_id, 'weekday']:
            check_in_is_valid = False
            message = f'{class_name} is not on today, so you cannot check in yet.'
    except KeyError:
        check_in_is_valid = False

    return check_in_is_valid, message


@bp.route('/')
@login_required
def show_classes():
    db = get_db()
    classes = QueryResult(db.get_all_classes())
    attendance = QueryResult(db.get_attendance(user_id=g.user['id']))
    if attendance:
        attendance = attendance[['class_id', 'user_id']].rename(columns={'user_id': 'Attendances'})
        attendance = attendance.groupby('class_id').count().reset_index()
        classes = QueryResult(classes.merge(attendance, on='class_id', how='left'))
    else:
        classes['Attendances'] = 0

    if classes:
        classes = classes[['class_name', 'weekday', 'class_time', 'end_time', 'Attendances']].fillna(0)
        # classes.sort_values(by=['weekday', 'class_time', 'class_name'], inplace=True)
        classes.rename(columns={
            'class_name': 'Class',
            'weekday': 'Day',
            'class_time': 'Start Time',
            'end_time': 'Finish Time'
        }, inplace=True)
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