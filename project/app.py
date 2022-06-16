from flask import request, render_template, redirect, url_for, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime
from __init__ import app, mysql
from models import Employees
from forms import HoursForm, LoginForm, HRSearchForm, SupvSearchForm, OnboardingForm
import pandas as pd
import pymysql

# Default route
@app.route('/')
def index():
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.close()
    conn.close()
    return render_template('index.html')

# Hours Sumbission route
@app.route('/hours', methods=['GET', 'POST'])
def hours():
    form = HoursForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        email = form.email.data
        password = form.password.data
        query = 'SELECT name, password FROM employees \
            WHERE email = "%s"'%email
        cur.execute(query)
        result = cur.fetchone()
        if check_password_hash(result['password'], password):
            name = result['name']
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
            return render_template('confirm.html')
        else:
            cur.close()
            conn.close()
            message = 'Invalid email/password.'
    # If the user input something incorrectly, one of these errors will be printed
    elif request.method == 'POST' and (not form.validate_on_submit()):
        for field, errors in form.errors.items():
            for error in errors:
                flash('Error in {}: {}'.format(
                    getattr(form, field).label.text, error
                ), 'error')
    return render_template('hours.html', form=form, message=message)


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
        query = 'SELECT * FROM employees WHERE email = "%s"'%email
        cur.execute(query)
        results = cur.fetchone()
        cur.close()
        conn.close()
        # Valid login
        if (results is not None and
            check_password_hash(results['password'], password)):
            # In HR
            user = Employees.query.filter_by(email=email).first()
            if results['is_hr'] == 1 and choice == 'hr':
                login_user(user)
                return redirect( url_for('hr'))
            # Is a supervisor
            elif results['is_supv'] == 1 and choice == 'supv':
                login_user(user)
                return redirect( url_for('supv'))
            # Unauthorized
            else: 
                message = 'You are not authorized to login in as your \
                    selection. If you meant to submit your hours, go \
                    back to the main hub and click on the correct link.'
        # Invalid login
        else:
            message = 'Invalid email/password.'
    return render_template('login.html', form=form, message=message)

# HR Hub route
@app.route('/hr', methods=['GET', 'POST'])
@login_required
def hr():
    message = ''
    form = HRSearchForm(request.form)
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
            query = 'SELECT id, name, date, clock_in, clock_out, pto, \
                hours, approval FROM timesheet WHERE name = "%s" \
                AND date BETWEEN "%s" AND "%s" ORDER BY name, date'%(name, 
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
            # Displays results in a table in a browser
            elif choice == 'browser':
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
@login_required
def supv():
    message = ''
    form = SupvSearchForm(request.form)
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
            query = 'SELECT supv FROM employees WHERE name = "%s"'%name
            cur.execute(query)
            supv = cur.fetchone()
            not_assigned = supv['supv'] != current_user.name
            # Supervisor is not assigned to the employee
            if not_assigned:
                message = 'You are not assigned as a supervisor for %s.'%name
            else:
                query = 'SELECT id, name, date, clock_in, clock_out, pto, \
                    hours, approval FROM timesheet WHERE name = "%s" \
                    AND date BETWEEN "%s" AND "%s" ORDER BY name, \
                    date'%(name, begin_conv, end_conv)
                cur.execute(query)
                results = cur.fetchall()
                cur.close()
                conn.close()
                # No results in the time frame
                if len(results) == 0:
                    message = 'There were no results for %s from %s \
                        to %s. If you were expecting results, please \
                        double check all fields.'%(name, begin_str, end_str)
                else:
                    return render_template('supvresults.html', results=results,
                        message='', first_id=results[0]['id'], 
                        last_id=results[len(results)-1]['id'])
    return render_template('supv.html', form=form, message=message)

# Supervisor Results route
@app.route('/supvresults', methods=['POST'])
@login_required
def supvresults():
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
        return render_template('supvresults.html', results=results, 
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
    return render_template('supvresults.html', results=results, 
        message=message, first_id=results[0]['id'], 
        last_id=results[len(results)-1]['id'])
    
# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('logout.html')

# Onboarding route
@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    form = OnboardingForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():
        conn = mysql.connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        address = request.form['address']
        phone = request.form['phone']
        is_hr = request.form['is_hr']
        supv = request.form['supv']
        is_supv = request.form['is_supv']
        query = 'INSERT INTO employees (name, email, password, \
            address, phone, is_hr, supv, is_supv) VALUES \
            ("%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s")'%(name, 
            email,  password, address, phone, is_hr, supv, is_supv)
        cur.execute(query)
        conn.commit()
        cur.close()
        conn.close()
        return render_template('confirm.html')
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
def page_not_found(e):
    return render_template('error.html', 
        pageheading="Unauthorized (Error 401)", error=e)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', 
        pageheading="Page not found (Error 404)", error=e)

@app.errorhandler(405)
def form_not_posted(e):
    return render_template('error.html', 
        pageheading="The form was not submitted (Error 405)", error=e)

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', 
        pageheading="Internal server error (500)", error=e)

if __name__ == '__main__':
    app.run()