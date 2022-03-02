from re import template
from tracemalloc import start
from flask import Blueprint, redirect, request, render_template, flash, url_for
from pandas import options
from nexusbjj.routes.auth import admin_required, login_required
from nexusbjj.forms import gen_form_item, gen_options
from nexusbjj.db import get_db, QueryResult, get_end_of_day
from datetime import datetime, timedelta


bp = Blueprint('reports', __name__, url_prefix='/reports', template_folder='templates/reports')


@bp.route('/attendance/headcount')
@admin_required
def headcount():
    today = datetime.today().date()
    db = get_db()
    class_date = today.strftime('%A, %d %b %Y')
    results, error = get_attendance(today.isoformat(), today.isoformat())
    if results:
        summary = results[['class_name', 'user_id']].groupby('class_name').count().reset_index()\
                                                  .rename(columns={
                                                            'class_name': 'Class',
                                                            'user_id': 'Attendees'
                                                         })\
                                                  .to_html(index=False)
    else:
        summary = QueryResult(db.get_classes(weekday=today.strftime('%A')))
        if summary:
            summary['Attendees'] = 0
            summary = summary[['class_name', 'Attendees']]
            summary.rename(columns={'class_name': 'Classes'})
        else:
            flash(f'No classes found for {class_date}.')
            return render_template('headcount.html')

    return render_template('headcount.html', result=summary, class_date=class_date)


@bp.route('/attendance/custom', methods=['GET', 'POST'])
@admin_required
def attendance_custom():
    groups = {
        'report': {
            'group_title': 'Generate Attendance Report'
        },
        'dates': {
            'start_picker': gen_form_item('start_date', label='Start Date', item_type='date', required=True),
            'end_picker': gen_form_item('end_date', label='End Date', item_type='date', required=True)
        },
        'submit': {
            'btn-submit': gen_form_item('btn-submit', item_type='submit', value='Submit')
        }
    }

    if request.method == 'POST':
        start_date = (request.form.get('start_date'))
        end_date = request.form.get('end_date')
        results, error = get_attendance(start_date, end_date)
        if results:
            return render_template('attendance.html', result=results.to_html(index=False), start_date=start_date,
                                   end_date=end_date)
        else:
            flash(error)

    return render_template('attendance.html', form_groups=groups)


@bp.route('/attendance/today')
@admin_required
def attendance_today():
    today = datetime.today().date().isoformat()
    results, error = get_attendance(today, today)
    if results:
            return render_template('attendance.html', result=results.to_html(index=False), start_date=today,
                                   end_date=today)
    else:
        flash(error)
        return redirect(url_for('reports.attendance_custom'))


@bp.route('/attendance/yesterday')
@admin_required
def attendance_yesterday():
    yesterday = (datetime.today().date() - timedelta(days=1)).isoformat()
    results, error = get_attendance(yesterday, yesterday)
    if results:
            return render_template('attendance.html', result=results.to_html(index=False), start_date=yesterday,
                                   end_date=yesterday)
    else:
        flash(error)
        return redirect(url_for('reports.attendance_custom'))


@bp.route('/attendance/last-week')
@admin_required
def attendance_last_week():
    today = datetime.today().date()
    last_sunday = today - timedelta(days=today.weekday()+1)
    last_monday = last_sunday - timedelta(days=7)
    results, error = get_attendance(last_monday, last_sunday)
    if results:
            return render_template('attendance.html', result=results.to_html(index=False), start_date=last_monday,
                                   end_date=last_sunday)
    else:
        flash(error)
        return redirect(url_for('reports.attendance_custom'))


@bp.route('/attendance/last-month')
@admin_required
def attendance_last_month():
    today = datetime.today().date()
    first_of_month = datetime(today.year, today.month - 1, 1)
    last_of_month = datetime(today.year, today.month, day=1, hour=23, minute=59, second=59) - timedelta(days=1)
    results, error = get_attendance(first_of_month, last_of_month)
    if results:
            return render_template('attendance.html', result=results.to_html(index=False), start_date=first_of_month,
                                   end_date=last_of_month)
    else:
        flash(error)
        return redirect(url_for('reports.attendance_custom'))


def get_attendance(start_date, end_date):
    error = ''
    if start_date == end_date:
        start_date = datetime.fromisoformat(start_date)
        end_date = (datetime.fromisoformat(end_date) + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        error = f'No classes were attended on {start_date.strftime("%A, %d %b %Y")}.'
    else:
        error = f'No classes were attended between {start_date.strftime("%A, %d %b %Y")} and '
        error += f'{end_date.strftime("%A, %d %b %Y")}.'

    db = get_db()
    results = QueryResult(db.get_attendance(start_date, end_date))
    
    if results:
        results.sort_values(by=['class_date', 'class_time', 'class_name', 'date'], inplace=True)
    
    return results, error
