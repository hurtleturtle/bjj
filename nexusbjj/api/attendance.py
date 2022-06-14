from flask import Blueprint, g, request
from nexusbjj.db import get_db, QueryResult
from datetime import datetime, timedelta
import json

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
    beginning_of_week = today - timedelta(days=today.weekday())
    total_attendance = db.get_attendance(from_date=beginning_of_week, to_date=today, user_id=user_id)
    membership = db.get_membership(user_id=user_id)
    
    result = {
        'membership': membership,
        'total_attendance': json.loads(QueryResult(total_attendance).to_json())
    }

    return result