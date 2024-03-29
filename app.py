from flask import request, render_template, redirect, url_for, current_app, \
    session
from flask_principal import Identity, AnonymousIdentity, Permission, \
    identity_changed, identity_loaded, RoleNeed, PermissionDenied
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.wrappers import Response
from __init__ import app, user, password, host, database
from forms import HREmployeeForm, HoursForm, LoginForm, HRGeneralForm, SupvHoursForm, \
    OnboardingForm, EmployHoursForm
from models import Employees
from datetime import datetime
from io import StringIO
import psycopg2
import csv

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
        conn = psycopg2.connect(host=host, database=database, user=user, 
            password=password)
        cur = conn.cursor()
        query = "SELECT roles FROM employees WHERE id = '%s'"%identity.id
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

# Default route
@app.route('/')
def index():
    message = ''
    # If the user was logged in when returning, they will be logged out
    if current_user.is_authenticated:
        logout_user()
        for key in ('identity.name', 'identity.auth_type'):
            session.pop(key, None)
        identity_changed.send(current_app._get_current_object(),
            identity=AnonymousIdentity())
        message = 'You have been logged out.'
    return render_template('index.html', message=message)

# HR/Supervisor Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        conn = psycopg2.connect(host=host, database=database, user=user, 
            password=password)
        cur = conn.cursor()
        email = request.form['email']
        pwd = request.form['password']
        choice = request.form['choice']
        query = "SELECT password FROM employees WHERE email = '%s'"%email
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        not_none = result is not None
        check_pass = check_password_hash(result[0], pwd)

        # Valid login, will be logged in to check permissions
        if not_none and check_pass:
            employee = Employees.query.filter_by(email=email).first()
            login_user(employee)
            identity_changed.send(current_app._get_current_object(),
                    identity=Identity(employee.id))
            try:
                # In HR
                if choice == 'hr':
                    with hr_permission.require():
                        return redirect( url_for('hr'))
                # Is a supervisor
                elif choice == 'supv':
                    with supv_permission.require():
                        return redirect( url_for('supv'))
                # Logging in to submit/adjust hours
                else:
                    return redirect( url_for('hours'))
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

# Employee Hub route
@app.route('/hours', methods=['GET', 'POST'])
@login_required
def hours():
    if request.method == 'POST':
        choice = request.form['choice']
        if choice == 'submit':
            return redirect( url_for('hours_submit'))
        else:
            return redirect( url_for('hours_search'))
    return render_template('hours.html', name=current_user.name)

# Hours Sumbission route
@app.route('/hours-submit', methods=['GET', 'POST'])
@login_required
def hours_submit():
    form = HoursForm()
    if request.method == 'POST' and form.validate_on_submit():
        conn = psycopg2.connect(host=host, database=database, user=user, 
            password=password)
        cur = conn.cursor()
        name = current_user.name
        date = request.form['date']
        clock_in = request.form['clock_in']
        clock_out = request.form['clock_out']
        pto = request.form['pto']
        hours = request.form['hours']
        approval = 'Not Approved'
        query = "INSERT INTO timesheet (name,  date, clock_in, \
            clock_out, pto, hours, approval) VALUES ('%s', '%s', \
            '%s', '%s', '%s', '%s', '%s')"%(name, date, clock_in, 
            clock_out, pto, hours, approval)
        cur.execute(query)
        conn.commit()
        cur.close()
        conn.close()
        return render_template('confirm.html', hours=True)
    return render_template('hours-submit.html', form=form)

# Hours View route
@app.route('/hours-search', methods=['GET', 'POST'])
@login_required
def hours_search():
    message = ''
    form = EmployHoursForm()
    if request.method == 'POST' and form.validate_on_submit():
        begin_str = request.form['date_begin']
        end_str = request.form['date_end']
        begin_conv = datetime.strptime(begin_str, '%Y-%m-%d').date()
        end_conv = datetime.strptime(end_str, '%Y-%m-%d').date()
        end_first = (end_conv < begin_conv)
        
        # End date is before begin date
        if end_first:
            message = 'The end date was before the begin date. \
                Please double check your dates.'
        else:
            conn = psycopg2.connect(host=host, database=database, user=user, 
                password=password)
            cur = conn.cursor()
            query = "SELECT * FROM timesheet WHERE name = '%s' \
                    AND date BETWEEN '%s' AND '%s' ORDER BY date"%(
                    current_user.name, begin_conv, end_conv)
            cur.execute(query)
            results = cur.fetchall()
            print(results)
            cur.close()
            conn.close()

            # No results in the time frame
            if len(results) == 0:
                message = 'There were no results from %s \
                    to %s. If you were expecting results, please \
                    double check all fields.'%(begin_str, end_str)
            else:
                return render_template('hours-results.html', results=results,
                    message='', first_id=results[0][0],
                    last_id=results[len(results) - 1][0])

    return render_template('hours-search.html', form=form, message=message)

# Adjust Hours route, should only be redirected from hours-adjust.html
# Used for employee and supervisor adjustment forms
@app.route('/hours-adjust', methods=['POST'])
@login_required
def hours_adjust():
    conn = psycopg2.connect(host=host, database=database, user=user, 
        password=password)
    cur = conn.cursor()
    id = request.form['id']
    name = request.form['name']
    date = request.form['date']
    clock_in = request.form['clock_in']
    clock_out = request.form['clock_out']
    pto = request.form['pto']
    hours = request.form['hours']
    approval = 'Not Approved'
    first_date = request.form['first_date']
    last_date = request.form['last_date']
    type = request.form['type']
    query = "UPDATE timesheet SET date = '%s', clock_in = '%s', \
        clock_out = '%s', pto = '%s', hours = '%s', approval = '%s' \
        WHERE id = '%s'"%(date, clock_in, clock_out, pto, hours, approval, id)
    cur.execute(query)
    conn.commit()
    if type == 'supv_all':
        query = "SELECT timesheet.id, timesheet.name, date, clock_in, \
            clock_out, pto, hours, approval, supv FROM timesheet INNER \
            JOIN employees ON employees.name=timesheet.name WHERE supv = \
            '%s' AND date BETWEEN '%s' AND '%s' ORDER BY name, date"%(
            current_user.name, first_date, last_date)
    else:
        query = "SELECT * FROM timesheet WHERE name = '%s' AND date BETWEEN \
            '%s' AND '%s' ORDER BY date"%(name, first_date, last_date)
    cur.execute(query)
    results = cur.fetchall()
    cur.close()
    conn.close()
    message = 'The entry has been updated and unapproved.'

    # Gets redirected to employee search results
    if type == 'employ':
        return render_template('hours-results.html', results=results, 
            message=message, first_id=results[0][0], 
            last_id=results[len(results) - 1][0])

    # Redirected to supverisor search results, only one employee searched
    elif type == 'supv':
        return render_template('supv-results.html', results=results, 
            message=message, first_id=results[0][0], 
            last_id=results[len(results) - 1][0], all_flag=False)

    # Redirected to supverisor search results, all employees searched
    else:
        return render_template('supv-results.html', results=results, 
            message=message, first_id=results[0][0], 
            last_id=results[len(results) - 1][0], all_flag=True)

# Hours Edit or Remove route
@app.route('/edit-or-remove', methods=['GET', 'POST'])
@login_required
def edit_or_remove():
    conn = psycopg2.connect(host=host, database=database, user=user, 
        password=password)
    cur = conn.cursor()
    choice = request.form['choice']
    id = request.form['id']
    first_date = request.form['first_date']
    last_date = request.form['last_date']

    # Action was edit
    if choice == 'edit':
        query = "SELECT * FROM timesheet WHERE id = '%s'"%id
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        form = HoursForm()
        return render_template('hours-adjust.html', result=result, 
            name=current_user.name, id=id,first_date=first_date, 
            last_date=last_date, form=form, type='employ')

    # Action was delete
    else:
        query = "DELETE FROM timesheet WHERE id = '%s'"%id
        cur.execute(query)
        conn.commit()
        query = "SELECT * FROM timesheet WHERE name = '%s' AND date BETWEEN \
            '%s' AND '%s' ORDER BY date"%(current_user.name, first_date, 
            last_date)
        cur.execute(query)
        results = cur.fetchall()
        cur.close()
        conn.close()
        message = 'The entry has been deleted.'
        return render_template('hours-results.html', results=results, 
            message=message, first_id=results[0][0], 
            last_id=results[len(results) - 1][0])

# Generates the CSV for HR
def generate_csv(results, name, begin_str, end_str):
    def generate():
        data = StringIO()
        w = csv.writer(data)
        cur_name = None
        total_hours = 0
        all_approved = True
        # Header
        w.writerow(('name', 'date', 'clock_in', 'clock_out', 
            'pto', 'hours', 'approval', 'total_hours', 'all_approved'))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # Data
        for record in results:
            # Same employee as the last write in
            if record[1] == cur_name:
                total_hours += record[6]
                rec_approve = record[7]
                all_approved = all_approved and rec_approve
                w.writerow((record[1], record[2], record[3], record[4], 
                    record[5], record[6], record[7]))
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)

            # Different employee
            else:
                # Not the first entry, creates the summary for the last employee
                if cur_name != None:
                    if all_approved:
                        w.writerow(('', '', '', '', '', '', '', total_hours,
                            'Approved'))
                    else:
                        w.writerow(('', '', '', '', '', '', '', total_hours,
                            'Not Approved'))
                    yield data.getvalue()
                    data.seek(0)
                    data.truncate(0)
                # Prepares for the next employee, writes in first entry for
                # the employee
                cur_name = record[1]
                total_hours = record[6]
                all_approved = record[7] == 'Approved'
                w.writerow((record[1], record[2], record[3], record[4], 
                    record[5], record[6], record[7]))
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)

        # Write in the last employee's summary
        w.writerow(('', '', '', '', '', '', '', total_hours,
            all_approved))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
    response = Response(generate(), mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', 
        filename="%s_%s_%s.csv"%(name, begin_str,
        end_str))
    return response

# HR Hub route
@app.route('/hr', methods=['GET', 'POST'])
@hr_permission.require()
def hr():
    message = ''
    form = HRGeneralForm()
    if request.method == 'POST':
        name = request.form['name']
        all_flag = name == 'all'
        search_edit = request.form['search_edit']

        # Edit employee info
        if search_edit == 'edit':
            # Cannot select 'All Employees' for this action
            if all_flag:
                message = 'You cannot select all employees for editing.'
            else:
                conn = psycopg2.connect(host=host, database=database, user=user, 
                    password=password)
                cur = conn.cursor()
                query = "SELECT * FROM employees WHERE name = '%s'"%name
                cur.execute(query)
                result = cur.fetchone()
                cur.close()
                conn.close()
                form = HREmployeeForm()
                return render_template('hr-employees.html', form=form, 
                    result=result)

        # Search timesheet
        else:
            begin_str = request.form['date_begin']
            end_str = request.form['date_end']
            # Begin and end date fields must be filled out
            if begin_str == '' or end_str == '':
                message = 'You must fill out the rest of this form if you are \
                    searching the timesheet.'
            else:
                export_choice = request.form['export_choice']
                begin_conv = datetime.strptime(begin_str, '%Y-%m-%d').date()
                end_conv = datetime.strptime(end_str, '%Y-%m-%d').date()
                end_first = (end_conv < begin_conv)

                # End date is before begin date
                if end_first:
                    message = 'The end date was before the begin date. \
                        Please double check your dates.'
                else:
                    conn = psycopg2.connect(host=host, database=database, 
                        user=user, password=password)
                    cur = conn.cursor()
                    results = ()

                    # If all employees were selected
                    if all_flag:
                        query = "SELECT * FROM timesheet WHERE date BETWEEN \
                            '%s' AND '%s' ORDER BY name, date"%(begin_conv, 
                            end_conv)
                        cur.execute(query)
                        results = cur.fetchall()
                        cur.close()
                        conn.close()
                        # No results in time frame
                        if len(results) == 0:
                            message = 'There were no results from %s \
                                to %s. If you were expecting results, please \
                                double check all fields.'%(begin_str, end_str)

                    # Only one employee was selected
                    else:
                        query = "SELECT * FROM timesheet WHERE name = '%s' \
                            AND date BETWEEN '%s' AND '%s' ORDER BY date"%(name, 
                            begin_conv, end_conv)
                        cur.execute(query)
                        results = cur.fetchall()
                        cur.close()
                        conn.close()
                        # No results in time frame
                        if len(results) == 0:
                            message = 'There were no results for %s from %s \
                                to %s. If you were expecting results, please \
                                double check all fields.'%(name, begin_str, 
                                end_str)

                    # No error messages
                    if message == '':
                        # Displays results in a table in a browser
                        if export_choice == 'browser':
                            return render_template('hr-results.html', 
                                results=results)
                        # Exports results in a CSV
                        else:
                            return generate_csv(results, name, begin_str, 
                                end_str)

    return render_template('hr.html', form=form, message=message)

# Employee Info Editing route
@app.route('/hr-employees', methods=['GET', 'POST'])
def hr_employees():
    message = ''
    id = request.form['id']
    choice = request.form['choice']
    conn = psycopg2.connect(host=host, database=database, user=user, 
        password=password)
    cur = conn.cursor()
    if choice == 'delete':
        query = "DELETE FROM timesheet WHERE id = '%s'"%id
        cur.execute(query)
        conn.commit()
        message = "The employee's information has been deleted."
    else:
        name = request.form['name']
        email = request.form['email']
        address = request.form['address']
        phone = request.form['phone']
        supv = request.form['supv']
        roles = request.form['roles']
        query = 'UPDATE employees SET name = "%s", email = "%s", \
            address = "%s" phone = "%s", supv = "%s", roles = "%s" \
            WHERE id = "%s" '%(name, email, address, phone, supv, roles, 
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
    form = SupvHoursForm(current_user.name)
    if request.method == 'POST':
        form = SupvHoursForm(current_user.name)
        name = request.form['name']
        begin_str = request.form['date_begin']
        end_str = request.form['date_end']
        begin_conv = datetime.strptime(begin_str, '%Y-%m-%d').date()
        end_conv = datetime.strptime(end_str, '%Y-%m-%d').date()
        end_first = (end_conv < begin_conv)
        # End date is before begin date
        if end_first:
            message = 'The end date was before the begin date. \
                Please double check your dates.'
        else:
            conn = psycopg2.connect(host=host, database=database, user=user, 
                password=password)
            cur = conn.cursor()
            all_flag = None

            # If all employees for the supervisor was selected
            if name == 'all':
                all_flag = True
                query = "SELECT timesheet.id, timesheet.name, date, clock_in, \
                    clock_out, pto, hours, approval, supv FROM timesheet INNER \
                    JOIN employees ON employees.name=timesheet.name WHERE supv = \
                    '%s' AND date BETWEEN '%s' AND '%s' ORDER BY name, date"%(
                    current_user.name, begin_conv, end_conv)
                cur.execute(query)
                results = cur.fetchall()
                cur.close()
                conn.close()
                # No results in the time frame
                if len(results) == 0:
                    message = 'There were no results from %s \
                        to %s. If you were expecting results, please \
                        double check all fields.'%(begin_str, end_str)

            # Only one specific employee was selected
            else:
                all_flag = False
                query = "SELECT * FROM timesheet WHERE name = '%s' \
                    AND date BETWEEN '%s' AND '%s' ORDER BY date"%(name, 
                    begin_conv, end_conv)
                cur.execute(query)
                results = cur.fetchall()
                cur.close()
                conn.close()
                # No results in the time frame
                if len(results) == 0:
                    message = 'There were no results for %s from %s \
                        to %s. If you were expecting results, please \
                        double check all fields.'%(name, begin_str, end_str)

            # If there are no error messages
            if message == '':
                return render_template('supv-results.html', results=results,
                    message=message, first_id=results[0][0], 
                    last_id=results[len(results)-1][0], all_flag=all_flag)

    return render_template('supv.html', form=form, message=message)

# Supervisor Results route
@app.route('/supv-results', methods=['POST'])
@supv_permission.require()
def supv_results():
    list = request.form.getlist('selection')
    conn = psycopg2.connect(host=host, database=database, user=user, 
        password=password)
    cur = conn.cursor()
    name = request.form['name']
    first_date = request.form['first_date']
    last_date = request.form['last_date']
    all_flag = request.form['all_flag']
    message = ''
    last_query = ''
    if all_flag:
        last_query = "SELECT timesheet.id, timesheet.name, date, clock_in, \
            clock_out, pto, hours, approval, supv FROM timesheet INNER \
            JOIN employees ON employees.name=timesheet.name WHERE supv = \
            '%s' AND date BETWEEN '%s' AND '%s' ORDER BY name, date"%(
            current_user.name, first_date, last_date)
    else:
        last_query = "SELECT * FROM timesheet WHERE name = '%s' AND date BETWEEN \
            '%s' AND '%s' ORDER BY name, date"%(name, first_date,
            last_date)

    # If no records were selected
    if len(list) == 0:
        cur.execute(last_query)
        results = cur.fetchall()
        message = 'You did not select any entries. Please select at least one \
            entry before proceeding.'
        cur.close()
        conn.close()
        return render_template('supv-results.html', results=results, 
            message=message, first_id=results[0][0], 
            last_id=results[len(results)-1][0], all_flag=all_flag)

    choice = request.form['choice']
    # Action is edit
    if choice == 'edit':
        # Checks to see if there is more than one entry selected
        if len(list) > 1:
            message = 'You can only edit one entry at a time.'
        else:
            id = list[0]
            query = "SELECT * FROM timesheet WHERE id = '%s'"%id
            cur.execute(query)
            result = cur.fetchone()
            cur.close()
            conn.close()
            form = HoursForm()
            if all_flag:
                return render_template('hours-adjust.html', result=result, 
                    name=name, id=id, first_date=first_date, 
                    last_date=last_date, form=form, type='supv_all')
            else:
                return render_template('hours-adjust.html', result=result, 
                    name=name, id=id, first_date=first_date, 
                    last_date=last_date, form=form, type='supv')

    # Action is delete
    elif choice == 'delete':
        for id in list:
            query = "DELETE FROM timesheet WHERE id = '%s'"%id
            cur.execute(query)
            conn.commit()
        message = 'The entry has been deleted.'

    # Action is approve
    elif choice == 'approve':
        for id in list:
            query = "UPDATE timesheet SET approval = 'Approved' WHERE \
                id = '%s'"%id
            cur.execute(query)
            conn.commit()
        message = 'All selected entries were approved.'

    # Action is unappove
    else:
        for id in list:
            query = "UPDATE timesheet SET approval = 'Not Approved' WHERE \
                id = '%s'"%id
            cur.execute(query)
            conn.commit()
        message = 'All selected entries were unapproved.'

    cur.execute(last_query)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('supv-results.html', results=results, 
        message=message, first_id=results[0][0], 
        last_id=results[len(results)-1][0], all_flag=all_flag)

# Onboarding route
@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    message = ''
    form = OnboardingForm()
    if request.method == 'POST' and form.validate_on_submit():
        conn = psycopg2.connect(host=host, database=database, user=user, 
            password=password)
        cur = conn.cursor()
        name = request.form['name']
        email = request.form['email']
        pwd = generate_password_hash(request.form['password'])
        address = request.form['address']
        phone = request.form['phone']
        supv = request.form['supv']
        roles = request.form['roles']
        query = "INSERT INTO employees (name, email, password, \
            address, phone, supv, roles) VALUES \
            ('%s', '%s', '%s', '%s', '%s', '%s', '%s')"%(name, 
            email,  pwd, address, phone, supv, roles)
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