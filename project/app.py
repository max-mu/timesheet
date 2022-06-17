from flask import request, render_template, redirect, url_for, flash, \
    send_file, current_app, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime
from __init__ import app, mysql
from models import Employees
from forms import HoursForm, LoginForm, HRSearchForm, SupvSearchForm, \
    OnboardingForm, EmploySearchForm
from flask_principal import Identity, AnonymousIdentity, Permission, \
    identity_changed, identity_loaded, RoleNeed, PermissionDenied
import pandas as pd
import pymysql

be_hr = RoleNeed('hr')
be_supv = RoleNeed('supv')
hr_permission = Permission(be_hr)
supv_permission = Permission(be_supv)

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

# Default route
@app.route('/')
def index():
    message = ''
    # If the user returned from an error, they will be logged out if they were
    # logged in.
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
        if (result is not None and
            check_password_hash(result['password'], password)):
            user = Employees.query.filter_by(email=email).first()
            login_user(user)
            identity_changed.send(current_app._get_current_object(),
                    identity=Identity(user.id))
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
@app.route('/hourssubmit', methods=['GET', 'POST'])
@login_required
def hours_submit():
    form = HoursForm()
    if request.method == 'POST' and form.validate_on_submit():
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        name = current_user.name
        date = request.form['date']
        clock_in = request.form['clock_in']
        clock_out = request.form['clock_out']
        pto = request.form['pto']
        hours = request.form['hours']
        approval = 'Not Approved'
        query = 'INSERT INTO timesheet (name,  date, clock_in, \
            clock_out, pto, hours, approval) VALUES ("%s", "%s", \
            "%s", "%s", "%s", "%s", "%s")'%(name, date, clock_in, 
            clock_out, pto, hours, approval)
        cur.execute(query)
        conn.commit()
        cur.close()
        conn.close()
        return render_template('confirm.html', hours=True)
    # If the user input something incorrectly, one of these errors will be printed
    elif request.method == 'POST' and (not form.validate_on_submit()):
        for field, errors in form.errors.items():
            for error in errors:
                flash('Error in {}: {}'.format(
                    getattr(form, field).label.text, error
                ), 'error')
    return render_template('hours_submit.html', form=form)

# Hours View route
@app.route('/hourssearch', methods=['GET', 'POST'])
@login_required
def hours_search():
    message = ''
    form = EmploySearchForm()
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
            conn = mysql.connect()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            query = 'SELECT id, name, date, clock_in, clock_out, pto, \
                    hours, approval FROM timesheet WHERE name = "%s" \
                    AND date BETWEEN "%s" AND "%s" ORDER BY date'%(
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
            else:
                return render_template('hoursresults.html', results=results,
                    first_flag=results[0]['id'])
    return render_template('hourssearch.html', form=form, message=message)

# Hours Adjust route
@app.route('/hoursresults', methods=['GET', 'POST'])
@login_required
def hours_results():
    pass

# HR Hub route
@app.route('/hr', methods=['GET', 'POST'])
@hr_permission.require()
def hr():
    message = ''
    form = HRSearchForm()
    if request.method == 'POST' and form.validate_on_submit():
        name = request.form['name']
        begin_str = request.form['date_begin']
        end_str = request.form['date_end']
        choice = request.form['choice']
        begin_conv = datetime.strptime(begin_str, '%Y-%m-%d').date()
        end_conv = datetime.strptime(end_str, '%Y-%m-%d').date()
        end_first = (end_conv < begin_conv)
        # End date is before begin date
        if end_first:
            message = 'The end date was before the begin date. \
                Please double check your dates.'
        else:
            conn = mysql.connect()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            results = ()
            if name == 'all':
                query = 'SELECT id, name, date, clock_in, clock_out, pto, \
                    hours, approval FROM timesheet WHERE date BETWEEN \
                    "%s" AND "%s" ORDER BY name, date'%(begin_conv, end_conv)
                cur.execute(query)
                results = cur.fetchall()
                cur.close()
                conn.close()
                # No results in time frame
                if len(results) == 0:
                    message = 'There were no results from %s \
                        to %s. If you were expecting results, please \
                        double check all fields.'%(begin_str, end_str)
            else:
                query = 'SELECT id, name, date, clock_in, clock_out, pto, \
                    hours, approval FROM timesheet WHERE name = "%s" \
                    AND date BETWEEN "%s" AND "%s" ORDER BY date'%(name, 
                    begin_conv, end_conv)
                cur.execute(query)
                results = cur.fetchall()
                cur.close()
                conn.close()
                # No results in time frame
                if len(results) == 0:
                    message = 'There were no results for %s from %s \
                        to %s. If you were expecting results, please \
                        double check all fields.'%(name, begin_str, end_str)
                if message == '':
                    # Displays results in a table in a browser
                    if choice == 'browser':
                        return render_template('hrresults.html', results=results)
                    # Exports results in a CSV
                    else:
                        conn = mysql.connect()
                        csv_results = pd.read_sql_query(query, conn)
                        df = pd.DataFrame(csv_results)
                        df.to_csv(r'results.csv', index=False)
                        conn.close()
                        return send_file('results.csv', as_attachment=True)
    return render_template('hr.html', form=form, message=message)

# Supervisor Hub route
@app.route('/supv', methods=['GET', 'POST'])
@supv_permission.require()
@login_required
def supv():
    message = ''
    form = SupvSearchForm(current_user.name)
    if request.method == 'POST' and form.validate_on_submit():
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
            conn = mysql.connect()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            if name == 'all':
                query = 'SELECT timesheet.id, timesheet.name, date, clock_in, \
                    clock_out, pto, hours, approval, supv FROM timesheet INNER \
                    JOIN employees ON employees.name=timesheet.name WHERE supv = \
                    "%s" AND date BETWEEN "%s" AND "%s" ORDER BY name, date'%(
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
            else:
                query = 'SELECT id, name, date, clock_in, clock_out, pto, \
                    hours, approval FROM timesheet WHERE name = "%s" \
                    AND date BETWEEN "%s" AND "%s" ORDER BY date'%(name, 
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
            if message == '':
                return render_template('supv_results.html', results=results,
                    message=message, first_id=results[0]['id'], 
                    last_id=results[len(results)-1]['id'])
    return render_template('supv.html', form=form, message=message)

# Supervisor Results route
@app.route('/supvresults', methods=['POST'])
@supv_permission.require()
def supv_results():
    list = request.form.getlist('selection')
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    name = request.form['name']
    date_begin = request.form['date_begin']
    date_end = request.form['date_end']
    message = ''
    if len(list) == 0:
        query = 'SELECT id, name, date, clock_in, clock_out, pto, hours, \
            approval FROM timesheet WHERE name = "%s" AND date BETWEEN \
            "%s" AND "%s" ORDER BY name, date'%(name, date_begin, 
            date_end)
        cur.execute(query)
        results = cur.fetchall()
        message = 'You did not select any entries. Please select at least one \
            entry before proceeding.'
        return render_template('supv_results.html', results=results, 
            message=message, first_id=results[0]['id'], 
            last_id=results[len(results)-1]['id'])
    choice = request.form['choice']
    if choice == 'approve':
        for id in list:
            query = 'UPDATE timesheet SET approval = "Approved" WHERE \
                id = "%s"'%id
            cur.execute(query)
            conn.commit()
    else:
        for id in list:
            query = 'UPDATE timesheet SET approval = "Not Approved" WHERE \
                id = "%s"'%id
            cur.execute(query)
            conn.commit()
    query = 'SELECT id, name, date, clock_in, clock_out, pto, hours, \
        approval FROM timesheet WHERE name = "%s" AND date BETWEEN \
        "%s" AND "%s" ORDER BY name, date'%(name, date_begin, 
        date_end)
    cur.execute(query)
    results = cur.fetchall()
    if choice == 'approve':
        message = 'All selected entries were approved.'
    else:
        message = 'All selected entries were unapproved.'
    return render_template('supv_results.html', results=results, 
        message=message, first_id=results[0]['id'], 
        last_id=results[len(results)-1]['id'])

# Onboarding route
@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    form = OnboardingForm()
    if request.method == 'POST' and form.validate_on_submit():
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        address = request.form['address']
        phone = request.form['phone']
        supv = request.form['supv']
        roles = request.form['roles']
        query = 'INSERT INTO employees (name, email, password, \
            address, phone, supv, roles) VALUES \
            ("%s", "%s", "%s", "%s", "%s", "%s", "%s")'%(name, 
            email,  password, address, phone, supv, roles)
        cur.execute(query)
        conn.commit()
        cur.close()
        conn.close()
        return render_template('confirm.html', hours=False)
    # The password fields are the only things that can invalidate the form
    elif request.method == 'POST' and (not form.validate_on_submit()):
        for field, errors in form.errors.items():
            for error in errors:
                flash('Error: {}'.format(
                    getattr(form, field).label.text, error
                ), 'error')
    return render_template('onboarding.html', form=form)

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
    app.run()