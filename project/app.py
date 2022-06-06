from flask import Flask, request, render_template, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from wtforms import SubmitField, StringField, PasswordField, DateField, FloatField, HiddenField, SelectField, RadioField
from flask_wtf import FlaskForm
from wtforms.validators import InputRequired
from flask_sqlalchemy import SQLAlchemy
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
    AUTH = 1
    UNAUTH = 2
    LOGINFAIL = 3

# Employee Model
class Employees(db.Model):
    __tablename__ = 'Employees'
    name = db.Column(db.String)
    email = db.Column(db.String, primary_key=True)
    password = db.Column(db.String)
    ishr = db.Column(db.Integer) # 0 for not in HR, 1 for in HR
    supervisor = db.Column(db.String)
    issupervisor = db.Column(db.Integer) # 0 for not a supervisor, 1 for supervisor

# Timesheet Model
class Timesheet(db.Model):
    __tablename__ = "Timesheet"
    name = db.Column(db.String)
    hours = db.Column(db.Float)
    date = db.Column(db.String, primary_key=True)
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

# Login Form
class LoginForm(FlaskForm):
    email = StringField(label='Email Address', validators=[InputRequired()])
    password = PasswordField(label='Password', validators=[InputRequired()])
    login = SubmitField(label='Login')

# Generates the list of names of employees for FetchForm
def get_name_choices():
    choices = [('', '')]
    list = Employees.query.order_by(Employees.name).distinct()
    for data in list:
        choices.append((data.name, data.name))
    return choices

# Fetch Form
class FetchForm(FlaskForm):
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
        if(data.ishr and type == 'hr') or (data.issupervisor and type == 'supv'):
            return Login.AUTH, data
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
        if result[0] == Login.AUTH: # Valid login, in HR
            return redirect( url_for('hr'))
        elif result[0] == Login.UNAUTH: # Valid login, not in HR
            message = 'You are not in the HR department. If you meant to submit your hours, go back and click on the correct link.'
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
        if result[0] == Login.AUTH: # Valid login, supervisor
            return redirect( url_for('supv', supvname=result[1].name))
        elif result[0] == Login.UNAUTH: # Valid login, not a supervisor
            message = 'You are not a supervisor. If you meant to submit your hours, go back and click on the correct link.'
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

if __name__ == '__main__':
    app.run()