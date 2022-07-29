from flask import request, render_template, redirect, url_for, current_app, \
    session
from flask_principal import Identity, AnonymousIdentity, Permission, \
    identity_changed, identity_loaded, RoleNeed, PermissionDenied
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.wrappers import Response
from __init__ import app, mysql
from forms import HREmployeeForm, HoursForm, LoginForm, HRGeneralForm, SupvForm, \
    OnboardingForm, EmployHoursForm
from models import Employees
from io import StringIO
from datetime import datetime, timedelta
import csv
import pymysql

# Flask-Principal Roles and Permissions
be_hr = RoleNeed('hr')
be_supv = RoleNeed('supv')
hr_permission = Permission(be_hr)
supv_permission = Permission(be_supv)

# When user logs in, any roles that are associated with the login is given
@identity_loaded.connect
def on_identity_loaded(sender, identity):
    if identity.id is not None:
        needs = []
        conn = mysql.connect()
        cur = conn.cursor()
        query = 'SELECT roles FROM employees WHERE id = "%s"'%identity.id
        cur.execute(query)
        role = cur.fetchone()
        if role[0] == 'hr':
            needs.append(be_hr)
        elif role[0] == 'supv':
            needs.append(be_supv)
        cur.close()
        conn.close()
        for n in needs:
            identity.provides.add(n)

# Converts dates from YYYYY/MM/DD to MM/DD/YYYY, returns string type
def convert_date(date):
    temp = datetime.strptime(date, '%Y-%m-%d')
    return str(temp.strftime('%m-%d-%Y'))

# Converts times from 24 hour to 12 hour, returns string type
def convert_time(time):
    t = datetime.strptime(time, "%H:%M")
    return str(t.strftime("%I:%M %p"))

# Returns the day of the week given the string of the date
def get_day_of_week(s):
    datetime_obj = datetime.strptime(s, '%Y-%m-%d').date()
    num_day = datetime_obj.weekday()
    if num_day == 0:
        return 'Mon'
    elif num_day == 1:
        return 'Tue'
    elif num_day == 2:
        return 'Wed'
    elif num_day == 3:
        return 'Thur'
    elif num_day == 4:
        return 'Fri'
    elif num_day == 5:
        return 'Sat'
    else:
        return 'Sun'

# Generates a CSV with the timesheet info given the data in results
def gen_timesheet_csv(results, name, date_begin, date_end):
    def generate():
        data = StringIO()
        w = csv.writer(data)
        cur_name = None
        total_hours = 0
        all_approved = True
        # Header
        w.writerow(('name', 'day_of_week', 'date', 'clock_in', 'clock_out', 
            'pto', 'hours', 'approval', 'total_hours', 'all_approved'))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # Data
        for record in results:
            # Same employee as the last write in
            if record['name'] == cur_name:
                total_hours += record['hours']
                rec_approve = record['approval']
                all_approved = all_approved and rec_approve
                w.writerow((record['name'], record['day_of_week'], 
                    record['date_conv'], record['in_conv'], 
                    record['out_conv'], record['pto'], 
                    record['hours'], record['approval']))
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)

            # Different employee
            else:
                # Not the first entry, creates the summary for the last employee
                if cur_name != None:
                    if all_approved:
                        w.writerow(('', '', '', '', '', '', '', '', total_hours,
                            'Approved'))
                    else:
                        w.writerow(('', '', '', '', '', '', '', '', total_hours,
                            'Not Approved'))
                    yield data.getvalue()
                    data.seek(0)
                    data.truncate(0)
                # Prepares for the next employee, writes in first entry for
                # the employee
                cur_name = record['name']
                total_hours = record['hours']
                all_approved = record['approval'] == 'Approved'
                w.writerow((record['name'], record['day_of_week'], 
                    record['date_conv'], record['in_conv'], 
                    record['out_conv'], record['pto'], 
                    record['hours'], record['approval']))
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)

        # Write in the last employee's summary
        if all_approved:
            w.writerow(('', '', '', '', '', '', '', '', total_hours,
                'Approved'))
        else:
            w.writerow(('', '', '', '', '', '', '', '', total_hours,
                'Not Approved'))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

    response = Response(generate(), mimetype='text/csv')
    begin_conv = convert_date(date_begin)
    end_conv = convert_date(date_end)
    response.headers.set('Content-Disposition', 'attachment', 
        filename='"%s"_"%s"_"%s".csv'%(name, begin_conv,
        end_conv))
    return response

# Generates a CSV with the employee info given the data in results
def gen_employee_csv(results, name):
    def generate():
        data = StringIO()
        w = csv.writer(data)

        # Header
        w.writerow(('name', 'email', 'address', 'phone'))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # Data
        for record in results:
            w.writerow((record['name'], record['email'],
                record['address'], record['phone']))
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
            
    response = Response(generate(), mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', 
        filename='"%s"_employee_info.csv'%(name))
    return response

# Default route
@app.route('/')
def index():
    # Logs out the user if returning from an error
    if current_user.is_authenticated:
        logout_user()
        for key in ('identity.name', 'identity.auth_type'):
            session.pop(key, None)
        identity_changed.send(current_app._get_current_object(),
            identity=AnonymousIdentity())
    return render_template('index.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        email = request.form['email']
        password = request.form['password']
        choice = request.form['choice']
        query = 'SELECT password FROM employees WHERE email = "%s"'%email
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()

        # Valid login, will be logged in to check permissions
        if result is not None and check_password_hash(result['password'], password):
            user = Employees.query.filter_by(email=email).first()
            login_user(user)
            identity_changed.send(current_app._get_current_object(),
                    identity=Identity(user.id))
            try:
                # In HR
                if choice == 'hr':
                    with hr_permission.require():
                        session.permanent = True
                        app.permanent_session_lifetime = timedelta(hours = 16)
                        return redirect( url_for('hr'))
                # Is a supervisor
                elif choice == 'supv':
                    with supv_permission.require():
                        session.permanent = True
                        app.permanent_session_lifetime = timedelta(hours = 16)
                        return redirect( url_for('supv'))
                # Logging in to submit/adjust hours
                else:
                    session.permanent = True
                    app.permanent_session_lifetime = timedelta(hours = 16)
                    return redirect( url_for('employee'))
            # Unauthorized, will be logged out and returned to login screen
            except PermissionDenied:
                message = 'You are not authorized to login in as your \
                    selection. If you meant to submit your hours, go \
                    back to the main hub and click on the correct link.'
                logout_user()
                identity_changed.send(current_app._get_current_object(),
                    identity=AnonymousIdentity())
        # Invalid login
        else:
            message = 'Invalid email/password.'
    return render_template('login.html', form=form, message=message)

# Logout route
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)
    identity_changed.send(current_app._get_current_object(),
        identity=AnonymousIdentity())
    return render_template('logout.html')

# Employee Hub route
@app.route('/employee', methods=['GET', 'POST'])
@login_required
def employee():
    if request.method == 'POST':
        choice = request.form['choice']
        if choice == 'submit':
            return redirect( url_for('hours_submit'))
        else:
            return redirect( url_for('hours_search'))
    return render_template('employee.html', name=current_user.name)

# Hours Sumbission route
@app.route('/hours-submit', methods=['GET', 'POST'])
@login_required
def hours_submit():
    form = HoursForm()
    if request.method == 'POST' and form.validate_on_submit():
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        name = current_user.name
        employ_id = current_user.id
        date = request.form['date']
        day_of_week = get_day_of_week(date)
        date_conv = convert_date(date)
        clock_in = request.form['clock_in']
        in_conv = convert_time(clock_in)
        clock_out = request.form['clock_out']
        out_conv = convert_time(clock_out)
        pto = request.form['pto']
        hours = request.form['hours']
        approval = 'Not Approved'
        query = 'INSERT INTO timesheet (name, employ_id, day_of_week, \
            date, date_conv, clock_in, in_conv, clock_out, out_conv, pto, \
            hours, approval) VALUES ("%s", "%s", "%s", "%s", "%s", "%s", "%s", \
            "%s", "%s", "%s", "%s", "%s")'%(name, employ_id, day_of_week, date, 
            date_conv, clock_in, in_conv, clock_out, out_conv, pto, hours, approval)
        cur.execute(query)
        result = [name, day_of_week, date_conv, in_conv, out_conv, 
            pto, hours]
        conn.commit()
        cur.close()
        conn.close()
        # Display submitted info
        return render_template('confirm.html', hours=True, result=result)
    return render_template('hours-submit.html', form=form)

# Hours View route
@app.route('/hours-search', methods=['GET', 'POST'])
@login_required
def hours_search():
    message = ''
    form = EmployHoursForm()
    if request.method == 'POST' and form.validate_on_submit():
        date_begin = request.form['date_begin']
        date_end = request.form['date_end']
        end_first = (date_end < date_begin)
        # End date is before begin date
        if end_first:
            message = 'The end date was before the begin date. \
                Please double check your dates.'
        else:
            conn = mysql.connect()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            query = 'SELECT * FROM timesheet WHERE employ_id = "%s" \
                    AND date BETWEEN "%s" AND "%s" ORDER BY date'%(
                    current_user.id, date_begin, date_end)
            cur.execute(query)
            results = cur.fetchall()
            cur.close()
            conn.close()

            # No results in the time frame
            if len(results) == 0:
                begin_conv = convert_date(date_begin)
                end_conv = convert_date(date_end)
                message = 'There were no results from %s \
                    to %s. If you were expecting results, please \
                    double check all fields.'%(begin_conv, end_conv)
            else:
                return render_template('hours-results.html', results=results,
                    message='', date_begin=date_begin, date_end=date_end)

    return render_template('hours-search.html', form=form, message=message)

# Adjust Hours route, should only be redirected from hours-adjust.html
# Used for employee and supervisor adjustment forms
@app.route('/hours-adjust', methods=['POST'])
@login_required
def hours_adjust():
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    id = request.form['id']
    employ_id = request.form['employ_id']
    date = request.form['date']
    day_of_week = get_day_of_week(date)
    date_conv = convert_date(date)
    clock_in = request.form['clock_in']
    in_conv = convert_time(clock_in)
    clock_out = request.form['clock_out']
    out_conv = convert_time(clock_out)
    pto = request.form['pto']
    hours = request.form['hours']
    approval = 'Not Approved'
    query = 'UPDATE timesheet SET day_of_week = "%s", date = "%s", \
        date_conv = "%s", clock_in = "%s", in_conv = "%s", clock_out = "%s", \
        out_conv = "%s", pto = "%s", hours = "%s", approval = "%s" WHERE id = "%s"\
        '%(day_of_week, date, date_conv, clock_in, in_conv, clock_out, out_conv, 
        pto, hours, approval, id)
    cur.execute(query)
    conn.commit()

    date_begin = request.form['date_begin']
    date_end = request.form['date_end']
    type = request.form['type']
    if type == 'supv_all':
        query = 'SELECT timesheet.*, supv_id FROM timesheet INNER \
            JOIN employees ON employees.id=timesheet.employ_id WHERE \
            (supv_id = "%s" OR employ_id = "%s") AND (date BETWEEN "%s" AND \
            "%s") ORDER BY name, date'%(current_user.id, current_user.id, 
            date_begin, date_end)
    else:
        query = 'SELECT * FROM timesheet WHERE employ_id = "%s" AND date BETWEEN \
            "%s" AND "%s" ORDER BY date'%(employ_id, date_begin, date_end)
    cur.execute(query)
    results = cur.fetchall()
    cur.close()
    conn.close()

    # No more results in the timeframe
    if len(results) == 0:
        message = 'The entry has been updated and unapproved. There were no more \
            entries that are in the specified timeframe.'
        if type == 'employ':
            form = EmployHoursForm()
            return render_template('hours-search.html', message=message,
                form=form)
        else:
            form = SupvForm(current_user.id)
            return render_template('supv.html', message=message, 
                form=form)

    message = 'The entry has been updated and unapproved.'
    # Redirected to employee search results
    if type == 'employ':
        return render_template('hours-results.html', results=results, 
            message=message, date_begin=date_begin, date_end=date_end)

    # Redirected to supverisor search results, only one employee searched
    elif type == 'supv':
        return render_template('supv-results.html', results=results, 
            message=message, date_begin=date_begin, date_end=date_end, 
            all_flag=False)

    # Redirected to supverisor search results, all employees searched
    else:
        return render_template('supv-results.html', results=results, 
            message=message, date_begin=date_begin, date_end=date_end, 
            all_flag=True)

# Hours Edit or Remove route
@app.route('/edit-or-remove', methods=['POST'])
@login_required
def edit_or_remove():
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    choice = request.form['choice']
    id = request.form['id']
    date_begin = request.form['date_begin']
    date_end = request.form['date_end']

    # Action was edit
    if choice == 'edit':
        query = 'SELECT * FROM timesheet WHERE id = "%s"'%id
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        form = HoursForm()
        return render_template('hours-adjust.html', result=result, 
            date_begin=date_begin, date_end=date_end, form=form,
            type='employ')

    # Action was delete
    else:
        query = 'DELETE FROM timesheet WHERE id = "%s"'%id
        cur.execute(query)
        conn.commit()
        query = 'SELECT * FROM timesheet WHERE employ_id = "%s" AND date \
            BETWEEN "%s" AND "%s" ORDER BY date'%(current_user.id, date_begin, 
            date_end)
        cur.execute(query)
        results = cur.fetchall()
        cur.close()
        conn.close()

        # No more results in the timeframe
        if len(results) == 0:
            message = 'The entry has been deleted and there were no more results in \
                the specified time frame.'
            form = EmployHoursForm()
            return render_template('hours-search.html', message=message, form=form)
        message = 'The entry has been deleted.'

        return render_template('hours-results.html', results=results, 
            message=message, date_begin=date_begin, date_end=date_end)

# HR Hub route
@app.route('/hr', methods=['GET', 'POST'])
@hr_permission.require()
def hr():
    message = ''
    form = HRGeneralForm()
    if request.method == 'POST':
        employ_id = request.form['employ_id']
        all_flag = employ_id == 'all'
        choice_1 = request.form['choice_1']

        # Edit employee info
        if choice_1 == 'edit':
            # Cannot select 'All Employees' for this action
            if all_flag:
                message = 'You cannot select all employees for editing.'
            else:
                conn = mysql.connect()
                cur = conn.cursor(pymysql.cursors.DictCursor)
                query = 'SELECT * FROM employees WHERE id = "%s"'%employ_id
                cur.execute(query)
                result = cur.fetchone()
                cur.close()
                conn.close()
                form = HREmployeeForm(supv_id=result['supv_id'], 
                    roles=result['roles'])
                edit_self = employ_id == str(current_user.id)
                return render_template('hr-employees.html', form=form, 
                    result=result, edit_self=edit_self)

        # Download employee info
        elif choice_1 == 'download':
            conn = mysql.connect()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            results = ''
            name = 'all' # Will get renamed if one employee was selected

            # If all employees was selected
            if all_flag:
                query = 'SELECT * FROM employees ORDER BY name'
                cur.execute(query)
                results = cur.fetchall()
            else:
                query = 'SELECT name FROM employees WHERE id = "%s" \
                    '%employ_id
                cur.execute(query)
                name = cur.fetchone()['name']
                query = 'SELECT * FROM employees WHERE id = "%s"'%employ_id
                cur.execute(query)
                results = cur.fetchall()
            cur.close()
            conn.close()
            return gen_employee_csv(results, name)

        # Search timesheet
        else:
            date_begin = request.form['date_begin']
            date_end = request.form['date_end']
            # Begin and end date fields must be filled out
            if date_begin == '' or date_end == '':
                message = 'You must fill out the rest of this form if you are \
                    searching the timesheet.'
            else:
                choice_2 = request.form['choice_2']
                end_first = (date_end < date_begin)

                # End date is before begin date
                if end_first:
                    message = 'The end date was before the begin date. \
                        Please double check your dates.'
                else:
                    name = 'all' # Will get renamed if one employee was selected
                    conn = mysql.connect()
                    cur = conn.cursor(pymysql.cursors.DictCursor)
                    results = ()

                    # If all employees were selected
                    if all_flag:
                        query = 'SELECT * FROM timesheet WHERE date BETWEEN \
                            "%s" AND "%s" ORDER BY name, date'%(date_begin, 
                            date_end)
                        cur.execute(query)
                        results = cur.fetchall()
                        cur.close()
                        conn.close()

                        # No results in time frame
                        if len(results) == 0:
                            begin_conv = convert_date(date_begin)
                            end_conv = convert_date(date_end)
                            message = 'There were no results from %s \
                                to %s. If you were expecting results, please \
                                double check all fields.'%(begin_conv, end_conv)

                    # Only one employee was selected
                    else:
                        query = 'SELECT name FROM employees WHERE id = "%s" \
                            '%employ_id
                        cur.execute(query)
                        name = cur.fetchone()['name']
                        query = 'SELECT * FROM timesheet WHERE employ_id = "%s" \
                            AND date BETWEEN "%s" AND "%s" ORDER BY date'%(employ_id, 
                            date_begin, date_end)
                        cur.execute(query)
                        results = cur.fetchall()
                        cur.close()
                        conn.close()

                        # No results in time frame
                        if len(results) == 0:
                            begin_conv = convert_date(date_begin)
                            end_conv = convert_date(date_end)
                            message = 'There were no results for %s from %s \
                                to %s. If you were expecting results, please \
                                double check all fields.'%(name, begin_conv, 
                                end_conv)
                    # No error messages
                    if message == '':
                        # Displays results in a table in a browser
                        if choice_2 == 'browser':
                            return render_template('hr-results.html', 
                                results=results)
                        # Exports results in a CSV
                        else:
                            return gen_timesheet_csv(results, name, date_begin, 
                                date_end)

    return render_template('hr.html', form=form, message=message)

# Employee Info Editing route
@app.route('/hr-employees', methods=['POST'])
def hr_employees():
    message = ''
    id = request.form['id']
    choice = request.form['choice']
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    if choice == 'delete':
        query = 'DELETE FROM employees WHERE id = "%s"'%id
        cur.execute(query)
        conn.commit()
        query = 'UPDATE employees SET supv_id = -1 WHERE supv_id = "%s"'%id
        cur.execute(query)
        conn.commit()
        query = 'DELETE FROM timesheet WHERE employ_id = "%s"'%id
        cur.execute(query)
        conn.commit()
        message = "The employee's information has been deleted."
    else:
        name = request.form['name']
        email = request.form['email']
        address = request.form['address']
        phone = request.form['phone']
        supv_id = request.form['supv_id']
        edit_self = request.form['edit_self']
        if edit_self == 'False':
            roles = request.form['roles']
            query = 'UPDATE employees SET name = "%s", email = "%s", \
                address = "%s", phone = "%s", supv_id = "%s", roles = "%s" \
                WHERE id = "%s"'%(name, email, address, phone, supv_id, roles, 
                id)
        else:
            query = 'UPDATE employees SET name = "%s", email = "%s", \
                address = "%s", phone = "%s", supv_id = "%s" WHERE id = \
                "%s"'%(name, email, address, phone, supv_id, id)
        cur.execute(query)
        conn.commit()
        query = 'UPDATE timesheet SET name = "%s" WHERE employ_id = "%s"'%(name, 
            id)
        cur.execute(query)
        conn.commit()
        message = "The employee's information has been edited."
    cur.close()
    conn.close()
    form = HRGeneralForm()
    return render_template('hr.html', form=form, message=message)

# Supervisor Hub route
@app.route('/supv', methods=['GET', 'POST'])
@supv_permission.require()
@login_required
def supv():
    message = ''
    form = SupvForm(current_user.id)
    if request.method == 'POST':
        employ_id = request.form['employ_id']
        date_begin = request.form['date_begin']
        date_end = request.form['date_end']
        end_first = (date_end < date_begin)
        # End date is before begin date
        if end_first:
            message = 'The end date was before the begin date. \
                Please double check your dates.'
        else:
            conn = mysql.connect()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            all_flag = employ_id == 'all'
            name = 'all' # Will get renamed if one employee was selected

            # If all employees for the supervisor was selected
            if all_flag:
                query = 'SELECT timesheet.*, supv_id FROM timesheet INNER \
                    JOIN employees ON employees.id=timesheet.employ_id WHERE \
                    (supv_id = "%s" OR employ_id = "%s") AND (date BETWEEN "%s" \
                    AND "%s") ORDER BY name, date'%(current_user.id, current_user.id, 
                    date_begin, date_end)
                cur.execute(query)
                results = cur.fetchall()
                cur.close()
                conn.close()
                
                # No results in the time frame
                if len(results) == 0:
                    begin_conv = convert_date(date_begin)
                    end_conv = convert_date(date_end)
                    message = 'There were no results from %s \
                        to %s. If you were expecting results, please \
                        double check all fields.'%(begin_conv, end_conv)

            # Only one specific employee was selected
            else:
                query = 'SELECT name FROM employees WHERE id = "%s" \
                    '%employ_id
                cur.execute(query)
                name = cur.fetchone()['name']
                query = 'SELECT * FROM timesheet WHERE employ_id = "%s" \
                    AND date BETWEEN "%s" AND "%s" ORDER BY date'%(employ_id, 
                    date_begin, date_end)
                cur.execute(query)
                results = cur.fetchall()
                cur.close()
                conn.close()
                
                # No results in the time frame
                if len(results) == 0:
                    begin_conv = convert_date(date_begin)
                    end_conv = convert_date(date_end)
                    message = 'There were no results for %s from %s \
                        to %s. If you were expecting results, please \
                        double check all fields.'%(name, begin_conv, end_conv)

            # If there are no error messages
            if message == '':
                return render_template('supv-results.html', results=results,
                    message=message, date_begin=date_begin, date_end=date_end, 
                    all_flag=all_flag)

    return render_template('supv.html', form=form, message=message)

# Supervisor Results route
@app.route('/supv-results', methods=['POST'])
@supv_permission.require()
def supv_results():
    list = request.form.getlist('selection')
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    employ_id = request.form['employ_id']
    date_begin = request.form['date_begin']
    date_end = request.form['date_end']
    all_flag = request.form['all_flag']
    choice = request.form['choice']
    message = ''
    last_query = ''
    # last_query will be used if redirected to supv-results.html
    if all_flag:
        last_query = 'SELECT timesheet.*, supv_id FROM timesheet INNER \
            JOIN employees ON employees.id=timesheet.employ_id WHERE \
            (supv_id = "%s" OR employ_id = "%s") AND (date BETWEEN "%s" AND \
            "%s") ORDER BY name, date'%(current_user.id, current_user.id, 
            date_begin, date_end)
    else:
        last_query = 'SELECT * FROM timesheet WHERE employ_id = "%s" AND date BETWEEN \
            "%s" AND "%s" ORDER BY name, date'%(employ_id, date_begin,
            date_end)

    # If no records were selected
    if len(list) == 0:
        cur.execute(last_query)
        results = cur.fetchall()
        message = 'You did not select any entries. Please select at least one \
            entry before proceeding.'
        cur.close()
        conn.close()
        return render_template('supv-results.html', results=results, 
            message=message, date_begin=date_begin, date_end=date_end, 
            all_flag=all_flag)

    # Action is edit
    if choice == 'edit':
        # Checks to see if there is more than one entry selected
        if len(list) > 1:
            message = 'You can only edit one entry at a time.'
        else:
            # Not redirected to supv-results, so last_query will not be used
            id = list[0]
            query = 'SELECT * FROM timesheet WHERE id = "%s"'%id
            cur.execute(query)
            result = cur.fetchone()
            cur.close()
            conn.close()
            form = HoursForm()
            if all_flag=='True':
                return render_template('hours-adjust.html', result=result, 
                    date_begin=date_begin, date_end=date_end, form=form, 
                    type='supv_all')
            else:
                return render_template('hours-adjust.html', result=result, 
                    date_begin=date_begin, date_end=date_end, form=form, 
                    type='supv')

    # Action is delete
    elif choice == 'delete':
        for id in list:
            query = 'DELETE FROM timesheet WHERE id = "%s"'%id
            cur.execute(query)
            conn.commit()
        message = 'The entry has been deleted.'

    # Action is approve
    elif choice == 'approve':
        for id in list:
            query = 'UPDATE timesheet SET approval = "Approved" WHERE \
                id = "%s"'%id
            cur.execute(query)
            conn.commit()
        message = 'All selected entries were approved.'

    # Action is unappove
    else:
        for id in list:
            query = 'UPDATE timesheet SET approval = "Not Approved" WHERE \
                id = "%s"'%id
            cur.execute(query)
            conn.commit()
        message = 'All selected entries were unapproved.'

    cur.execute(last_query)
    results = cur.fetchall()
    cur.close()
    conn.close()

    # Check for no more entries in timeframe, only can occur from deleting
    if len(results) == 0:
        message = 'The entry has been deleted and there were no more results in \
            the specified time frame.'
        form = SupvForm(current_user.id)
        return render_template('supv.html', message=message, form=form)

    return render_template('supv-results.html', results=results, 
        message=message, date_begin=date_begin, date_end=date_end, 
        all_flag=all_flag)

# Onboarding route
@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    message = ''
    form = OnboardingForm()
    if request.method == 'POST' and form.validate_on_submit():
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        address = request.form['address']
        phone = request.form['phone']
        # Setting default values
        supv_id = -1
        roles = 'none'
        query = 'INSERT INTO employees (name, email, password, \
            address, phone, supv_id, roles) VALUES ("%s", "%s", "%s", "%s", \
            "%s", "%s", "%s")'%(name, email, password, address, phone, supv_id, 
            roles)
        cur.execute(query)
        conn.commit()
        cur.close()
        conn.close()
        return render_template('confirm.html', hours=False)
    # The password fields are the only things that can invalidate the form
    elif request.method == 'POST' and (not form.validate_on_submit()):
        message = "Your password fields didn't match."
    return render_template('onboarding.html', form=form, message=message)

# Error routes
@app.errorhandler(401)
def unauthorized(e):
    return render_template('error.html', error=e, 
        pageheading="Unauthorized (Error 401)", 
        logged_in=current_user.is_authenticated)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error=e,
        pageheading="Page not found (Error 404)", 
        logged_in=current_user.is_authenticated)

@app.errorhandler(405)
def form_not_posted(e):
    return render_template('error.html', error=e,
        pageheading="The form was not submitted (Error 405)", 
        logged_in=current_user.is_authenticated)

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error=e,
        pageheading="Internal server error (500)",
        logged_in=current_user.is_authenticated)

if __name__ == '__main__':
    app.run(host='0.0.0.0')