from tracemalloc import start
from flask import Blueprint, make_response, redirect, request, render_template, flash, url_for, g
from nexusbjj.routes.auth import admin_required
from nexusbjj.forms import gen_form_item
from nexusbjj.db import get_db, QueryResult
from datetime import datetime, timedelta
from typing import Tuple
import pandas as pd
from calendar import day_name


bp = Blueprint('reports', __name__, url_prefix='/reports', template_folder='templates/reports')


# Attendance Reports


@bp.route('/attendance/headcount')
@admin_required
def headcount(export_to_csv=False):
    today = datetime.today()
    db = get_db()
    class_date = today.strftime('%A, %d %b %Y')
    classes = pd.DataFrame(db.get_classes(weekday=today.strftime('%A'))).sort_values(by='class_time')
    results, error = get_attendance(today.isoformat(), today.isoformat(), headcount=True)
    total_attendance, error = get_attendance(today.replace(day=1).isoformat(), today.isoformat(), headcount=True)
    title = 'Headcount'

    if not classes.empty:
        if results:
            summary = results[['class_id', 'user_id']].groupby('class_id').count().rename(columns={'user_id': 'Attendees'})
            summary = classes.merge(summary, left_on='id', right_index=True, how='outer')
        else:
            summary = classes
            summary['Attendees'] = 0
        
        summary = summary[['id', 'class_name', 'Attendees']].fillna(0)
        summary['Attendees'] = summary['Attendees'].astype(int)
        summary.rename(columns={'class_name': 'Class'}, inplace=True)
    else:
        flash(f'No classes found for {class_date}.')
        return render_template('report.html')

    print(results)
    return render_template('headcount.html', table_data=QueryResult(summary), attendance=results, page_title=title, table_title=title,
                            to_csv=False)


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
def absentees(export_to_csv=False):
    db = get_db()
    today = datetime.today()
    start = today - timedelta(days=14)
    title = 'Absentees'
    sub_title = f'No classes attended since {format_time(start)}'
    attendance = QueryResult(pd.DataFrame(db.get_absentees(from_date=start)).fillna('None'))

    if export_to_csv:
        return attendance
    else:
        attendance = QueryResult(attendance[['full_name', 'last_class']])

    return render_template('report.html', table_data=attendance, page_title=title, table_title=title, table_subtitle=sub_title, to_csv=True,
                           report='absentees', start_date=today.date().isoformat(), end_date=today.date().isoformat())


@bp.route('/users/exceeding-membership-limit')
@admin_required
def users_exceeding_membership_limit(export_to_csv=False):
    today = datetime.today()
    start_of_month = today.replace(day=1)
    end_of_last_month = start_of_month - timedelta(days=1)
    start_of_last_month = end_of_last_month.replace(day=1)
    
    user_attendance_this_month, error = get_attendance(start_of_last_month, today, headcount=True, 
                                                       extra_query_columns=['sessions_per_week', 'child_id'],
                                                       extra_result_columns=['sessions_per_week', 'child_id'])
    users = user_attendance_this_month[['user_id', 'child_id', 'full_name']].drop_duplicates().set_index(['user_id', 'child_id'])

    df_analysis = user_attendance_this_month.set_index('check_in_time').groupby(['user_id', 'child_id'], dropna=False).resample('1W-MON', label='left')\
                                            .agg({'class_id': 'count', 'sessions_per_week': 'min'})\
                                            .rename(columns={'class_id':'attendance'}).unstack().fillna(0)
    df_analysis['sessions', 'weekly_average'] = df_analysis['attendance'].mean(axis='columns').round(2)
    df_analysis['sessions', 'limit'] = df_analysis['sessions_per_week'].max(axis=1).astype(int)
    df_analysis= df_analysis[df_analysis['sessions', 'weekly_average'] > df_analysis['sessions', 'limit']]
    attendance = df_analysis['attendance'].astype(int)
    df_analysis.drop(columns=['sessions_per_week', 'attendance'], inplace=True)
    df_analysis.columns.names = [None, None]    

    column_index = pd.MultiIndex.from_product([['attendance'], pd.to_datetime(attendance.columns).date], names=[None, None])

    df_analysis = df_analysis.join(pd.DataFrame(attendance.to_numpy(), index=attendance.index, columns=column_index))
    df_analysis.index = users.loc[df_analysis.index]['full_name']
    df_analysis.index.name = None

    if export_to_csv:
        return df_analysis.to_csv()

    return render_template('report.html', table_html=df_analysis.to_html(classes='table'),
                           table_title='Users Exceeding Membership Limit', page_title='Excess Sessions', report='excess_attendances',
                           to_csv=True, start_date=start_of_last_month.date().isoformat(), end_date=today.date().isoformat()) 


# Class Reports


@bp.route('/classes/total-attendance')
@admin_required
def class_totals(export_to_csv=False):
    db = get_db()
    classes = QueryResult(db.get_all_classes())
    title = 'Class Attendances'
    attendance = QueryResult(db.get_attendance())
    today = datetime.today().date().isoformat()

    classes['weekday'] = convert_weekday_categorical(classes['weekday'])
    classes.rename(columns={'weekday': 'Day', 'class_name': 'Class', 'class_time': 'start_time', 'id': 'class_id'}, inplace=True)
    classes = classes[['class_id', 'Day', 'Class', 'start_time', 'end_time']]

    if attendance:
        attendance = attendance.set_index('check_in_time').groupby('class_id').resample('1W-MON', label='left')['user_id']\
                               .count().unstack()
        attendance = pd.DataFrame(attendance, index=attendance.index, columns=pd.to_datetime(attendance.columns).date)
        total_attendances = attendance.sum(axis='columns')
        attendance.insert(loc=0, column='Attendance', value=total_attendances)
        if not export_to_csv:
            attendance = attendance.reset_index()[['class_id', 'Attendance']]

        classes = classes.merge(attendance, on='class_id', how='left')
    else:
        classes['Attendance'] = 0

    classes[attendance.columns] = classes[attendance.columns].fillna(0).astype(int)

    if export_to_csv:
        classes = QueryResult(classes.sort_values(by=['Day', 'start_time']))
    else:
        classes = QueryResult(classes.sort_values(by=['Day', 'start_time'])[['Day', 'Class', 'Attendance']])

    if export_to_csv:
        return classes

    return render_template('report.html', table_data=classes, page_title=title, table_title=title, to_csv=True, start_date=today,
                           end_date=today, report='class_totals')


# Helpers


@bp.route('/csv')
@admin_required
def csv():
    attendance_report_requested = request.args.get('report')
    attendance_function = {
        'today': attendance_today,
        'yesterday': attendance_yesterday,
        'last_week': attendance_last_week,
        'last_month': attendance_last_month,
        'excess_attendances': users_exceeding_membership_limit,
        'absentees': absentees,
        'class_totals': class_totals
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

    if not isinstance(df_report, str):
        df_report = df_report.to_csv(index=False)

    response = make_response(df_report)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=' + filename
    return response



def get_attendance(start_date, end_date, brief=False, headcount=False, query_columns=None, extra_query_columns=None, 
                   result_columns=None, extra_result_columns=None, sort=True) -> Tuple[QueryResult, str]:
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
            for col in ('class_id', 'user_id', 'child_id', 'id', 'confirmed_by'):
                if col not in columns:
                    columns.append(col)

        if extra_result_columns:
            for col in extra_result_columns:
                if col not in columns:
                    columns.append(col)        
        
        results = QueryResult(results[columns])
        results.fillna(0, inplace=True)
    
    return results, error


@bp.route('/summarise')
def summarise_attendance(start_date=None, end_date=None):
    if not end_date:
        end_date = datetime.today()
    if not start_date:
        start_date = end_date - timedelta(days=end_date.weekday())

    db = get_db()
    attendance, error = get_attendance(start_date, end_date, headcount=True)
    attendance_today = attendance[attendance['class_date'] == end_date.date()]
    users = attendance_today['user_id'].unique().astype(str)
    memberships_condition = 'users.id IN ({})'.format(', '.join(['%s'] * len(users)))

    memberships = QueryResult(db.get_memberships(conditions=memberships_condition, params=tuple(users)))
    memberships['child_id'] = 0
    memberships = memberships.set_index(['user_id', 'child_id'])['sessions_per_week']
    children = QueryResult(db.get_children(users, extra_columns=['sessions_per_week'], 
                                           extra_table_clause='JOIN memberships ON membership_id=memberships.id'))
    children = children.rename(columns={'id': 'child_id', 'parent_id': 'user_id'}).set_index(['user_id', 'child_id'])['sessions_per_week']
    memberships = pd.concat([memberships, children])

    summary = attendance[['user_id', 'child_id', 'id']].groupby(['user_id', 'child_id'], dropna=False)\
                                                       .count()\
                                                       .rename(columns={'id': 'sessions_attended'})
    attendance_today = attendance_today.set_index(['user_id', 'child_id']).join(summary)
    attendance_today = attendance_today.join(memberships)
    attendance_today['sessions_remaining'] = attendance_today['sessions_per_week'] - attendance_today['sessions_attended']

    return attendance_today.to_html()


def format_time(time):
    if type(time) == str:
        time = datetime.fromisoformat(time)
    return time.strftime('%A, %d %b %Y')


def convert_weekday_categorical(column):
    return pd.Categorical(column, categories=list(day_name), ordered=True)


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