from flask import request, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from __init__ import app, db
from models import Employees, Timesheet
from forms import HoursForm, LoginForm, FetchForm
import enum

class Login(enum.Enum):
    HR = 1
    SUPV = 2
    UNAUTH = 3
    LOGINFAIL = 4

# Used in submitting hours, checks to see if the email and password are a valid login
def valid_login(e, password):
    data = Employees.query.filter_by(email=e).first() # Should only return one result anyways
    if(data != None and data.password == password):
        return True, data.name
    return False, ''

# Used in HR/Supervisor login, checks to see if the email and password are a valid login
# If login is valid, checks to see if the person logging in is in HR/Supervisor
def restrict_login(e, password, type):
    data = Employees.query.filter_by(email=e).first() # Should only return one result anyways
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
    print(error)
    if error == 'unauth':
        message = 'You are not authorized to login in as your selection. \
        If you meant to submit your hours, go back to the main hub and click on the correct link.'
    elif error == 'fail':
        message = 'Invalid email/password.'
    elif error == 'url':
        message = 'You must enter your login credentials in order to log in.'
    return render_template('login.html', message=message)

@app.route('/logincheck', methods=['POST'])
def logincheck():
    email = request.form['email']
    password = request.form['password']
    choice = request.form['choice']
    # result is a (Login, SQ query) tuple
    result = restrict_login(email, password, choice)
    if result[0] == Login.HR: # Valid login, in HR
        return redirect( url_for('loginsucess'))
    elif result[0] == Login.SUPV: # Valid login, supervisor
        return redirect( url_for('loginsucess'))
    elif result[0] == Login.UNAUTH: # Valid login, unauthorized
        return redirect( url_for('login', error='unauth'))
    elif result[0] == Login.LOGINFAIL:
        return redirect( url_for('login', error='fail')) 
    else:
        return redirect( url_for('login', error='url'))

@app.route('/loginsuccess', methods=['POST'])
def loginsuccess():
    form = FetchForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        name = form.name.data
        dateBegin = form.dateBegin.data
        dateEnd = form.dateEnd.data
        return redirect( url_for('hrresults', name=name, dateBegin=dateBegin, dateEnd=dateEnd))
    # If the user input something incorrectly, one of these errors will be printed                
    elif request.method == 'POST' and (not form.validate_on_submit()):
        message = 'Please formate the date(s) as mm/dd/yyyy.'
    return render_template('hr.html', form=form, message=message)

# HR Login route
@app.route('/hrlogin', methods=['GET', 'POST'])
def hrlogin():
    form = LoginForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        # result is a (Login, SQ query) tuple
        # The SQ query is not used here
        result = restrict_login(email, password, 'hr')
        if result[0] == Login.HR: # Valid login, in HR
            return redirect( url_for('hr'))
        elif result[0] == Login.UNAUTH: # Valid login, not in HR
            message = 'You are not in the HR department. \
                If you meant to submit your hours, go back and click on the correct link.'
        else:
            message = 'Invalid email/password.'
    return render_template('hrlogin.html', form=form, message=message)

# HR Hub route
@app.route('/hr', methods=['GET', 'POST'])
def hr():
    form = FetchForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        name = form.name.data
        dateBegin = form.dateBegin.data
        dateEnd = form.dateEnd.data
        return redirect( url_for('hrresults', name=name, dateBegin=dateBegin, dateEnd=dateEnd))
    # If the user input something incorrectly, one of these errors will be printed                
    elif request.method == 'POST' and (not form.validate_on_submit()):
        message = 'Please formate the date(s) as mm/dd/yyyy.'
    return render_template('hr.html', form=form, message=message)

# HR Results route
@app.route('/hrresults/<name>/<dateBegin>/<dateEnd>', methods=['GET', 'POST'])
def hrresults(name, dateBegin, dateEnd):
    list = Timesheet.query.filter_by(name=name).order_by(Timesheet.date).all()
    begin = datetime.strptime(dateBegin, '%Y-%m-%d').date()
    end = datetime.strptime(dateEnd, '%Y-%m-%d').date()
    filtered = []
    for data in list:
        date = datetime.strptime(data.date, '%m/%d/%Y').date()
        if begin <= date and date <= end:
            filtered.append(data)
    return render_template('hrresults.html', filtered=filtered, name=name, isEmpty=(len(filtered) > 0))

# Supervisor Login route
@app.route('/supvlogin', methods=['GET', 'POST'])
def supvlogin():
    form = LoginForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        # result is a (Login, SQ query) tuple
        result = restrict_login(email, password, 'supv')
        if result[0] == Login.SUPV: # Valid login, supervisor
            return redirect( url_for('supv', supvname=result[1].name))
        elif result[0] == Login.UNAUTH: # Valid login, not a supervisor
            message = 'You are not a supervisor. \
                If you meant to submit your hours, go back and click on the correct link.'
        else:
            message = 'Invalid email/password.'
    return render_template('supvlogin.html', form=form, message=message)

# Supervisor Hub route
@app.route('/supv/<supvname>', methods=['GET', 'POST'])
def supv(supvname):
    form = FetchForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        name = form.name.data
        data = Employees.query.filter_by(name=name).first() # There should only be 1 result
        super = data.supervisor
        if super == supvname:
            dateBegin = form.dateBegin.data
            dateEnd = form.dateEnd.data
            return redirect( url_for('supvresults', supvname=supvname, name=name, dateBegin=dateBegin, dateEnd=dateEnd))
        else:
            message = 'You are not a supervisor for this employee.'
    # If the user input something incorrectly, one of these errors will be printed                
    elif request.method == 'POST' and (not form.validate_on_submit()):
        message = 'Please formate the date(s) as mm/dd/yyyy.'
    return render_template('supv.html', form=form, message=message)

# Supervisor Results route
@app.route('/supvresults/<supvname>/<name>/<dateBegin>/<dateEnd>', methods=['GET', 'POST'])
def supvresults(supvname, name, dateBegin, dateEnd):
    list = Timesheet.query.filter_by(name=name).order_by(Timesheet.date).all()
    begin = datetime.strptime(dateBegin, '%Y-%m-%d').date()
    end = datetime.strptime(dateEnd, '%Y-%m-%d').date()
    filtered = []
    for data in list:
        date = datetime.strptime(data.date, '%m/%d/%Y').date()
        if begin <= date and date <= end:
            filtered.append(data)
    return render_template('supvresults.html', filtered=filtered, supvname=supvname, name=name, isEmpty=(len(filtered) > 0))

# Supervisor Approval/Unapproval route
@app.route('/supvedits/<supvname>/<name>', methods=['POST'])
def supvedits(supvname, name):
    date = request.form['date']
    choice = request.form['choice']
    entry = Timesheet.query.filter_by(name=name).filter(Timesheet.date == date).first()
    redun = (entry.approval == 'Yes' and choice == 'approve') or (entry.approval == 'No' and choice == 'unapprove')
    if not redun:
        if choice == 'approve':
            entry.approval = 'Yes'
        else:
            entry.approval = 'No'
        db.session.commit()
    return render_template('supvedits.html', supvname=supvname, choice=choice, redun=redun)
    
if __name__ == '__main__':
    app.run()