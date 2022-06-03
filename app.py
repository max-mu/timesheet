from flask import Flask, request, render_template, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_manager, login_user, login_required, logout_user
from wtforms import SubmitField, StringField, PasswordField, DateField, FloatField, HiddenField, SelectField
from flask_wtf import FlaskForm
from wtforms.validators import InputRequired
from datetime import datetime
import enum

app = Flask(__name__)
# TODO: Change this key in the end
app.config['SECRET_KEY'] = 'not a secure key'
Bootstrap(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timesheet.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

class Login(enum.Enum):
    VALID = 1
    INVALID = 2
    LOGINFAIL = 3

# Employee Table
class Employees(db.Model):
    __tablename__ = 'Employees'
    name = db.Column(db.String)
    email = db.Column(db.String, primary_key=True)
    password = db.Column(db.String)
    ishr = db.Column(db.Integer) # 0 for not in HR, 1 for in HR
    supervisor = db.Column(db.String)
    issupervisor = db.Column(db.Integer) # 0 for not a supervisor, 1 for supervisor

# Timesheet Table
class Timesheet(db.Model):
    __tablename__ = "Timesheet"
    name = db.Column(db.String, primary_key=True)
    hours = db.Column(db.Float)
    date = db.Column(db.String)
    approval = db.Column(db.String)

    def __init__(self, name, hours, date, approval):
        self.name = name
        self.hours = hours
        self.date = date
        self.approval = approval

# Hours Submission Form
class HoursForm(FlaskForm):
    email = StringField(label='Email Address', validators=[InputRequired()])
    password = PasswordField(label='Password', validators=[InputRequired()])
    hours = FloatField(label='Hours you worked', validators=[InputRequired()])
    date = DateField(label='Date (formatted as mm/dd/yyyy)', 
        validators=[InputRequired()], format='%m/%d/%Y')
    approved = HiddenField()
    submit = SubmitField(label='Submit')

# HR Login Form
class HRLoginForm(FlaskForm):
    email = StringField(label='Email Address', validators=[InputRequired()])
    password = PasswordField(label='Password', validators=[InputRequired()])
    login = SubmitField(label='Login')

# Supervisor Login Form
class SupvLoginForm(FlaskForm):
    email = StringField(label='Email Address', validators=[InputRequired()])
    password = PasswordField(label='Password', validators=[InputRequired()])
    login = SubmitField(label='Login')

# Generates the list of names of employees for HRForm
def get_name_choices():
    choices = [('', '')]
    list = Employees.query.order_by(Employees.name).distinct()
    for data in list:
        choices.append((data.name, data.name))
    return choices

# HR Form
class HRForm(FlaskForm):
    name = SelectField(label='Name of the employee', 
        validators=[InputRequired()], choices=get_name_choices())
    dateBegin = DateField(label='First date you want your search to contain (formatted as mm/dd/yyyy)', 
        validators=[InputRequired()], format='%m/%d/%Y')
    dateEnd = DateField(label='Last date you want your search to contain (formatted as mm/dd/yyyy)', 
        validators=[InputRequired()], format='%m/%d/%Y')
    submit = SubmitField(label='Submit')

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
    if(data != None and data.password == password):
        if(data.ishr and type == 'HR') or (data.issupervisor and type == 'supv'):
            return Login.VALID
        else:
            return Login.INVALID
    return Login.LOGINFAIL

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
        # tup is a (bool, string) pair
        tup = valid_login(email, password)
        if tup[0]:
            name = tup[1]
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

# HR Login route
@app.route('/hrlogin', methods=['GET', 'POST'])
def hrlogin():
    form = HRLoginForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        result = restrict_login(email, password, 'HR')
        if result == Login.VALID: # Valid login, in HR
            return redirect( url_for('hr'))
        elif result == Login.INVALID: # Valid login, not in HR
            message = 'You are not in the HR department. If you meant to submit your hours, go back and click on the correct link.'
        else:
            message = 'Invalid email/password.'
    return render_template('hrlogin.html', form=form, message=message)

# HR Hub route
@app.route('/hr', methods=['GET', 'POST'])
def hr():
    form = HRForm(request.form)
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
def hr_results(name, dateBegin, dateEnd):
    list = Timesheet.query.filter_by(name=name).order_by(Timesheet.date).all()
    begin = datetime.strptime(dateBegin, '%Y-%m-%d').date()
    end = datetime.strptime(dateEnd, '%Y-%m-%d').date()
    filtered = []
    for data in list:
        date = datetime.strptime(data.date, '%m/%d/%Y').date()
        if begin <= date and date <= end:
            filtered.append(data)
    return render_template('hrresults.html', filtered=filtered, name=name, isEmpty=(len(filtered) > 0))

@app.route('/supvlogin', methods=['GET', 'POST'])
def supv_login():
    form = SupvLoginForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        result = restrict_login(email, password, 'supv')
        if result == Login.VALID: # Valid login, supervisor
            return redirect( url_for('supv'))
        elif result == Login.INVALID: # Valid login, supervisor
            message = 'You are not a supervisor. If you meant to submit your hours, go back and click on the correct link.'
        else:
            message = 'Invalid email/password.'
    return render_template('supvlogin.html', form=form, message=message)

@app.route('/supv', methods=['GET', 'POST'])
def supv():
    return render_template('supv.html')

if __name__ == '__main__':
    app.run()