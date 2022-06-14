from flask import Blueprint, g, request
from nexusbjj.db import get_db, QueryResult
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