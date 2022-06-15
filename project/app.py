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
            return redirect(url_for('confirm'))
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

# Hours Confirmation route
@app.route('/confirm')
def confirm():
    return render_template('confirm.html')

# Login route
@app.route('/login/<error>')
def login(error):
    message = ''
    form = LoginForm()
    if error == 'unauth':
        message = 'You are not authorized to login in as your selection. \
        If you meant to submit your hours, go back to the main hub and \
        click on the correct link.'
    elif error == 'fail':
        message = 'Invalid email/password.'
    return render_template('login.html', form=form, message=message)

@app.route('/logincheck', methods=['POST'])
def logincheck():
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
    user = Employees.query.filter_by(email=email).first()
    # Valid login
    if len(results) != 0 and check_password_hash(results['password'], password):
        # In HR
        if results['is_hr'] == 1 and choice == 'hr':
            login_user(user)
            return redirect( url_for('hr'))
        # Is a supervisor
        elif results['is_supv'] == 1 and choice == 'supv':
            login_user(user)
            return redirect( url_for('supv'))
        # Unauthorized
        else: 
            return redirect( url_for('login', error='unauth'))
    # Invalid login
    return redirect( url_for('login', error='fail')) 

# HR Hub route
@app.route('/hr', methods=['GET', 'POST'])
@login_required
def hr():
    form = HRSearchForm(request.form)
    return render_template('hr.html', form=form)

# HR Results route
@app.route('/hrresults', methods=['POST'])
@login_required
def hrresults():
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    name = request.form['name']
    dateBegin = request.form['dateBegin']
    dateEnd = request.form['dateEnd']
    choice = request.form['choice']
    begin = datetime.strptime(dateBegin, '%Y-%m-%d').date()
    end = datetime.strptime(dateEnd, '%Y-%m-%d').date()
    end_first = (end < begin)
    results = ()
    if not end_first:
        query = 'SELECT id, name, date, clock_in, clock_out, pto, \
            hours, approval FROM timesheet WHERE name = "%s" \
            AND date BETWEEN "%s" AND "%s" ORDER BY date'%(name, begin, end)
        cur.execute(query)
        results = cur.fetchall()
    if choice == 'browser' or len(results) == 0 or end_first:
        return render_template('hrresults.html', end_first=end_first, 
        results=results,  name=name, dateBegin=dateBegin, 
        dateEnd=dateEnd, empty=(len(results) == 0))
    else:
        csv_results = pd.read_sql_query(query, conn)
        df = pd.DataFrame(csv_results)
        df.to_csv(r'results.csv', index=False)
        cur.close()
        conn.close()
        return send_file('results.csv', as_attachment=True)

# Supervisor Hub route
@app.route('/supv', methods=['GET', 'POST'])
@login_required
def supv():
    form = SupvSearchForm(request.form)
    return render_template('supv.html', form=form)

# Supervisor Results route
@app.route('/supvresults', methods=['POST'])
@login_required
def supvresults():
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    name = request.form['name']
    dateBegin = request.form['dateBegin']
    dateEnd = request.form['dateEnd']
    begin = datetime.strptime(dateBegin, '%Y-%m-%d').date()
    end = datetime.strptime(dateEnd, '%Y-%m-%d').date()
    not_assigned = None
    results = ()
    end_first = (end < begin)
    if not end_first:
        query = 'SELECT supv FROM employees WHERE name = "%s"'%name
        cur.execute(query)
        supv = cur.fetchone()
        not_assigned = supv['supv'] != current_user.name
        if not not_assigned:
            query = 'SELECT id, name, date, clock_in, clock_out, \
                pto, hours,approval FROM timesheet WHERE name = "%s" \
                AND date BETWEEN "%s" AND "%s" ORDER BY date'%(name, begin, end)
            cur.execute(query)
            results = cur.fetchall()
        cur.close()
        conn.close()
    return render_template('supvresults.html', end_first=end_first, 
        not_assigned=not_assigned, results=results, name=name, 
        dateBegin=dateBegin, dateEnd=dateEnd, empty=(len(results) == 0))

# Supervisor Approval/Unapproval route
@app.route('/supvedits', methods=['POST'])
@login_required
def supvedits():
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    id = request.form['id']
    choice = request.form['choice']
    query = 'SELECT approval FROM timesheet WHERE id = %s'
    cur.execute(query, [id])
    result = cur.fetchone()
    # If the state of the record is what the user selected, redun is True
    redun = ((result['approval'] == 'Approved' and choice == 'approve')
        or (result['approval'] == 'Not Approved' and choice == 'unapprove'))
    # Changes the state of the record
    if not redun:
        if choice == 'approve':
            query = 'UPDATE timesheet SET approval = "Approved" \
                WHERE id = "%s"'%id
        else:
            query = 'UPDATE timesheet SET approval = "Not Approved" \
                WHERE id = "%s"'%id
        cur.execute(query)
        conn.commit()
    cur.close()
    conn.close()
    return render_template('supvedits.html', choice=choice, redun=redun)
    
# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('logout.html')

@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    form = OnboardingForm(request.form)
    message = ''
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
        return redirect(url_for('confirm'))
    # The password fields are the only things that can invalidate the form
    elif request.method == 'POST' and (not form.validate_on_submit()):
        for field, errors in form.errors.items():
            for error in errors:
                flash('Error: {}'.format(
                    getattr(form, field).label.text, error
                ), 'error')
    return render_template('onboarding.html', form=form)

# Error route
@app.route('/error/<error>')
def error(error):
    return 'An error has occured: %s'%error

if __name__ == '__main__':
    app.run()