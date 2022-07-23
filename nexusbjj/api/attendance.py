from flask import Blueprint, g, request
from nexusbjj.db import get_db, QueryResult
from nexusbjj.routes.auth import get_user_from_token
from nexusbjj.routes.classes import get_todays_classes
from datetime import datetime, timedelta
import pandas as pd


bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')


@bp.route('/confirm-check-in')
def confirm_check_in():
    attendance_record_id = request.args.get('attendance_record_id')
    coach_id = request.args.get('coach_id')
    db = get_db()
    return db.confirm_check_in(attendance_record_id, coach_id)


@bp.route('/classes-remaining')
def get_remaining_classes():
    user_id = request.args.get('user_id')
    db = get_db()
    today = datetime.today()
    beginning_of_week = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0)
    total_attendance = QueryResult(db.get_attendance(from_date=beginning_of_week, to_date=today, user_id=user_id))
    membership = db.get_membership(user_id=user_id)
    users = QueryResult(db.get_children(user_id, extra_columns=['sessions_per_week'], 
                                           extra_table_clause='JOIN memberships ON membership_id=memberships.id'))

    users = pd.concat([users.rename(columns={'id': 'child_id', 'parent_id': 'user_id'}), pd.DataFrame([{
        'user_id': int(user_id),
        'membership_id': membership['id'],
        'sessions_per_week': membership['sessions_per_week'],
        'child_id': 0
    }])], ignore_index=True)
    users = users.join(total_attendance[['id', 'child_id']].groupby('child_id', dropna=False).count(), on='child_id')
    users = users.rename(columns={'id': 'sessions_attended'})
    users['sessions_attended'] = users['sessions_attended'].fillna(0).astype(int)
    users['sessions_remaining'] = users['sessions_per_week'] - users['sessions_attended']

    return {'result': users.to_dict('records')}


@bp.route('/check-in')
def check_in():
    class_id = request.args.get('class_id')
    child_id = request.args.get('child_id')
    user_id = g.user['id']

    if not user_id:
        msg = {'error': 'forbidden'}
        return msg, 401
    
    classes = get_todays_classes(user_id)
    classes = toggle_check_in(classes, class_id, user_id, child_id)

    return classes[['id', 'class_name', 'user_id', 'child_id', 'attendance']].to_json(orient='records')


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
            mask = (df_classes['attendance'] == False)
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

    return df_classes