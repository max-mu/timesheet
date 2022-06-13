from flask import request, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user
from datetime import datetime
from __init__ import app, db, mysql
from models import Employees, Timesheet
from forms import HoursForm, LoginForm, SearchForm
import enum

cur = mysql.connection.cursor()

class Login(enum.Enum):
    HR = 1
    SUPV = 2
    UNAUTH = 3
    LOGINFAIL = 4

# Used in submitting hours, checks to see if the email and password are a valid login
def valid_login(e, password):
    data = Employees.query.filter_by(email=e).first() # Should only return one result
    if(data != None and data.password == password):
        return True, data.name
    return False, ''

# Used in HR/Supervisor login, checks to see if the email and password are a valid login
# If login is valid, checks to see if the person logging in is a supervisor/HR
def restrict_login(e, password, type):
    data = Employees.query.filter_by(email=e).first() # Should only return one result
    if data != None and data.password == password:
        if data.ishr and type == 'hr':
            return Login.HR, None
        elif data.issupervisor and type == 'supv':
            return Login.SUPV, data
        else:
            return Login.UNAUTH, None
    return Login.LOGINFAIL, None

# Default route
@app.route('/')
def index():
    cur = mysql.connection.cursor()
    return render_template('index.html')

# Hours Sumbission route
@app.route('/hours', methods=['GET', 'POST'])
def hours():
    form = HoursForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        # result is a (bool, string) tuple
        result = valid_login(email, password)
        if result[0]:
            name = result[1]
            hours = request.form['hours']
            date = request.form['date']
            approval = 'No'
            record = Timesheet(name, hours, date, approval)
            db.session.add(record)
            db.session.commit()
            return render_template('confirm.html')
        else:
            message = 'Invalid email/password.'
    # If the user input something incorrectly, one of these errors will be printed
    elif request.method == 'POST' and (not form.validate_on_submit()):
        if not isinstance(form.hours.data, (int, float)):
            message = 'Please enter a numerical value for your hours.'
        else:
            message = 'Please formate the date as mm/dd/yyyy.'
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
        If you meant to submit your hours, go back to the main hub and click on the correct link.'
    elif error == 'fail':
        message = 'Invalid email/password.'
    elif error == 'url':
        message = 'You must enter your login credentials in order to log in.'
    return render_template('login.html', form=form, message=message)

@app.route('/logincheck', methods=['POST'])
def logincheck():
    email = request.form['email']
    password = request.form['password']
    choice = request.form['choice']
    # result is a (Login, SQ query) tuple
    result = restrict_login(email, password, choice)
    user = Employees.query.filter_by(email=email).first() # Should be only one result
    # Valid login, in HR
    if result[0] == Login.HR: 
        login_user(user)
        return redirect( url_for('hr'))
    # Valid login, supervisor
    elif result[0] == Login.SUPV: 
        login_user(user)
        return redirect( url_for('supv', supvname=result[1].name))
    # Valid login, unauthorized
    elif result[0] == Login.UNAUTH: 
        return redirect( url_for('login', error='unauth'))
    # Invalid login
    elif result[0] == Login.LOGINFAIL: 
        return redirect( url_for('login', error='fail')) 
    # If the user puts in the url and doesn't put in login credentials
    else:
        return redirect( url_for('login', error='url'))

# HR Hub route
@app.route('/hr', methods=['GET', 'POST'])
@login_required
def hr():
    form = SearchForm(request.form)
    return render_template('hr.html', form=form)

# HR Results route
@app.route('/hrresults', methods=['POST'])
@login_required
def hrresults():
    name = request.form['name']
    dateBegin = request.form['dateBegin']
    dateEnd = request.form['dateEnd']
    list = Timesheet.query.filter_by(name=name).order_by(Timesheet.date).all()
    filtered = []
    begin = datetime.strptime(dateBegin, '%Y-%m-%d').date()
    end = datetime.strptime(dateEnd, '%Y-%m-%d').date()
    end_first = (end < begin)
    if not end_first:
        for data in list:
            date = datetime.strptime(data.date, '%Y-%m-%d').date()
            if begin <= date and date <= end:
                filtered.append(data)
    return render_template('hrresults.html', end_first=end_first, filtered=filtered, 
        name=name, dateBegin=dateBegin, dateEnd=dateEnd, empty=(len(filtered) == 0))

# Supervisor Hub route
@app.route('/supv/<supvname>', methods=['GET', 'POST'])
@login_required
def supv(supvname):
    form = SearchForm(request.form)
    return render_template('supv.html', form=form, supvname=supvname)

# Supervisor Results route
@app.route('/supvresults/<supvname>', methods=['POST'])
@login_required
def supvresults(supvname):
    name = request.form['name']
    dateBegin = request.form['dateBegin']
    dateEnd = request.form['dateEnd']
    list = Timesheet.query.filter_by(name=name).order_by(Timesheet.date).all()
    filtered = []
    begin = datetime.strptime(dateBegin, '%Y-%m-%d').date()
    end = datetime.strptime(dateEnd, '%Y-%m-%d').date()
    end_first = (end < begin)
    employ = Employees.query.filter_by(name=name).first() # Should only return one result
    # This will needed to be changed if there can be more than one supervisor
    not_assigned = (employ.supervisor != supvname)
    if not not_assigned and not end_first:
        for data in list:
            date = datetime.strptime(data.date, '%Y-%m-%d').date()
            if begin <= date and date <= end:
                filtered.append(data)
    return render_template('supvresults.html', end_first=end_first, 
        not_assigned=not_assigned, filtered=filtered, supvname=supvname, name=name, 
        dateBegin=dateBegin, dateEnd=dateEnd, empty=(len(filtered) == 0))

# Supervisor Approval/Unapproval route
@app.route('/supvedits/<supvname>', methods=['POST'])
@login_required
def supvedits(supvname):
    date = request.form['date']
    choice = request.form['choice']
    entry = Timesheet.query.filter_by(date=date).filter(Timesheet.date == date).first()
    # If the state of the record is what the user selected, redun is True
    redun = ((entry.approval == 'Yes' and choice == 'approve')
        or (entry.approval == 'No' and choice == 'unapprove'))
    # Changes the state of the record
    if not redun:
        if choice == 'approve':
            entry.approval = 'Yes'
        else:
            entry.approval = 'No'
        db.session.commit()
    return render_template('supvedits.html', supvname=supvname, choice=choice, redun=redun)
    
# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('logout.html')

if __name__ == '__main__':
    app.run()