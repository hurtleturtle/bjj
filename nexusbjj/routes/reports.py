from re import template
from tracemalloc import start
from flask import Blueprint, make_response, redirect, request, render_template, flash, url_for
from pandas import options
from nexusbjj.routes.auth import admin_required, login_required
from nexusbjj.forms import gen_form_item, gen_options
from nexusbjj.db import get_db, QueryResult, get_end_of_day
from datetime import datetime, timedelta


bp = Blueprint('reports', __name__, url_prefix='/reports', template_folder='templates/reports')


# Attendance Reports

@bp.route('/attendance/headcount')
@admin_required
def headcount(export_to_csv=False):
    today = datetime.today()
    db = get_db()
    class_date = today.strftime('%A, %d %b %Y')
    results, error = get_attendance(today.isoformat(), today.isoformat(), headcount=True)
    if results:
        summary = QueryResult(results[['class_name', 'user_id']].groupby('class_name').count().reset_index()\
                                                                .rename(columns={
                                                                    'class_name': 'Class',
                                                                    'user_id': 'Attendees'
                                                                }))
    else:
        summary = QueryResult(db.get_classes(weekday=today.strftime('%A')))
        if summary:
            summary['Attendees'] = 0
            summary = summary[['class_name', 'Attendees']]
            summary.rename(columns={'class_name': 'Classes'})
        else:
            flash(f'No classes found for {class_date}.')
            return render_template('report.html')

    return get_report_template(QueryResult(summary), today, today, 'Headcount', 'Headcount', to_csv=False)


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
        start_date = datetime.fromisoformat(request.form.get('start_date'))
        end_date = datetime.fromisoformat(request.form.get('end_date'))
        results, error = get_attendance(start_date, end_date)
        if results:
            return get_report_template(results, start_date, end_date, 'custom')
        else:
            flash(error)

    return render_template('report.html', form_groups=groups)


@bp.route('/attendance/today')
@admin_required
def attendance_today(export_to_csv=False):
    today = datetime.today()
    results, error = get_attendance(today, today, brief=True)

    if export_to_csv:
        return results

    if results:
        return get_report_template(results, today, today, 'today')
    else:
        flash(error)
        return redirect(url_for('reports.attendance_custom'))


@bp.route('/attendance/yesterday')
@admin_required
def attendance_yesterday(export_to_csv=False):
    yesterday = (datetime.today() - timedelta(days=1))
    results, error = get_attendance(yesterday, yesterday, brief=True)

    if export_to_csv:
        return results

    if results:
        return get_report_template(results, yesterday, yesterday, 'yesterday')
    else:
        flash(error)
        return redirect(url_for('reports.attendance_custom'))


@bp.route('/attendance/last-week')
@admin_required
def attendance_last_week(export_to_csv=False):
    today = datetime.today()
    last_sunday = today - timedelta(days=today.weekday()+1)
    last_monday = last_sunday - timedelta(days=7)
    results, error = get_attendance(last_monday, last_sunday)

    if export_to_csv:
        return results

    if results:
        return get_report_template(results, last_monday, last_sunday, 'last_week')
    else:
        flash(error)
        return redirect(url_for('reports.attendance_custom'))


@bp.route('/attendance/last-month')
@admin_required
def attendance_last_month(export_to_csv=False):
    today = datetime.today()
    first_of_month = datetime(today.year, today.month - 1, 1)
    last_of_month = datetime(today.year, today.month, day=1) - timedelta(days=1)
    results, error = get_attendance(first_of_month, last_of_month)

    if export_to_csv:
        return results

    if results:
        return get_report_template(results, first_of_month, last_of_month, 'last_month')
    else:
        flash(error)
        return redirect(url_for('reports.attendance_custom'))


# User Reports


@bp.route('/users/absentees')
@admin_required
def absentees():
    pass


@bp.route('/users/exceeding-membership-limit')
@admin_required
def users_exceeding_membership_limit():
    db = get_db()
    today = datetime.today()
    start_of_month = today.replace(day=1)
    end_of_last_month = start_of_month - timedelta(days=1)
    start_of_last_month = end_of_last_month.replace(day=1)
    
    user_attendance_this_month, error = get_attendance(start_of_month, today, headcount=True, extra_query_columns=['sessions_per_week'],
                                                       extra_result_columns=['sessions_per_week'])
    #df_analysis = user_attendance_this_month.groupby('full_name').agg({'class_id': 'count', 'sessions_per_week': 'min'})
    df_analysis = user_attendance_this_month.pivot('check_in_time', 'full_name', ['class_id', 'sessions_per_week'])
    #df_analysis = df_analysis.resample('1W', level=1).agg({'class_id': 'count', 'sessions_per_week': 'min'})
    
    #df_analysis = QueryResult(df_analysis.rename(columns={'class_id': 'avg_classes_attended_per_week'}))
    #df_analysis['avg_classes_attended_per_week'] = (df_analysis['avg_classes_attended_per_week'] / 7).round(2)

    # TODO: resample df wih full name/user id as columns then reshape

    return get_report_template(QueryResult(df_analysis), start_of_month, today, 'users_exceeding_membership_limit', show_index=True)


# Helpers


@bp.route('/csv')
@admin_required
def csv():
    attendance_report_requested = request.args.get('report')
    attendance_function = {
        'today': attendance_today,
        'yesterday': attendance_yesterday,
        'last_week': attendance_last_week,
        'last_month': attendance_last_month
    }
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filename = attendance_report_requested + '_' + start_date

    if start_date != end_date:
        filename += '_' + end_date
    
    filename += '.csv'

    if attendance_report_requested == 'custom':
        df_report = get_attendance(start_date, end_date)[0]
    else:
        df_report = attendance_function[attendance_report_requested](export_to_csv=True)

    response = make_response(df_report.to_csv(index=False))
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=' + filename
    return response



def get_attendance(start_date, end_date, brief=False, headcount=False, query_columns=None, extra_query_columns=None, 
                   result_columns=None, extra_result_columns=None, sort=True):
    error = ''
    start_date = datetime.fromisoformat(start_date) if type(start_date) == str else start_date
    end_date = datetime.fromisoformat(end_date) if type(end_date) == str else end_date
    extra_args = {}

    if query_columns:
        extra_args['columns'] = query_columns
    if extra_query_columns:
        extra_args['extra_columns'] = extra_query_columns

    if start_date == end_date:  
        error = f'No classes were attended on {start_date.strftime("%A, %d %b %Y")}.'
    else:
        error = f'No classes were attended between {start_date.strftime("%A, %d %b %Y")} and '
        error += f'{end_date.strftime("%A, %d %b %Y")}.'

    start_date = start_date.replace(hour=0, minute=0, second=0)
    end_date = end_date.replace(hour=23, minute=59, second=59)
    db = get_db()

    attendance_keyword_args = {}
    if query_columns:
        attendance_keyword_args['columns'] = query_columns
    if extra_query_columns:
        attendance_keyword_args['extra_columns'] = extra_query_columns

    results = QueryResult(db.get_attendance(start_date, end_date, **attendance_keyword_args))

    if results:
        if sort:
            results.sort_values(by=['class_date', 'class_time', 'class_name', 'check_in_time'], inplace=True)
        
        if brief:
            columns= ['class_name', 'full_name', 'check_in_time']
        elif result_columns:
            columns = result_columns
        else:
            columns = ['class_name', 'class_date', 'class_time', 'full_name', 'check_in_time', 'membership_type']
        
        if headcount:
            for col in ('class_id', 'user_id'):
                if col not in columns:
                    columns.append(col)

        if extra_result_columns:
            for col in extra_result_columns:
                if col not in columns:
                    columns.append(col)        
        
        results = QueryResult(results[columns])
    
    return results, error


def format_time(time):
    if type(time) == str:
        time = datetime.fromisoformat(time)
    return time.strftime('%A, %d %b %Y')


def format_start_and_end(start_date, end_date):
    result = format_time(start_date)
    if end_date != start_date:
        result += ' - ' + format_time(end_date)

    return result


def get_report_template(results, start_date, end_date, report, title='Attendance', to_csv=True, show_index=False):
    sub_title = format_start_and_end(start_date, end_date)
    return render_template('report.html', table_data=results , page_title=title, table_title=title, table_subtitle=sub_title,
                           start_date=start_date.date().isoformat(), end_date=end_date.date().isoformat(), to_csv=to_csv, report=report,
                           show_index=show_index)