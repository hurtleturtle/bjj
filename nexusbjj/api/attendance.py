from flask import Blueprint, g, request
from nexusbjj.db import get_db
from datetime import datetime

bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')


@bp.route('/confirm-check-in')
def confirm_check_in():
    attendance_record_id = request.args.get('attendance_record_id')
    coach_id = request.args.get('coach_id')
    db = get_db()
    return db.confirm_check_in(attendance_record_id, coach_id)


def get_remaining_classes(user_id):
    db = get_db()
    today = datetime.today()
    total_attendance = db.get_attendance(from_date=today.replace(day=1), to_date=today, columns='*')