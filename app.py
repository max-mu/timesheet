from flask import Flask, request, render_template, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from wtforms import SubmitField, StringField, PasswordField, DateField, FloatField, HiddenField, SelectField
from flask_wtf import FlaskForm
from wtforms.validators import InputRequired
from datetime import datetime
import enum

app = Flask(__name__)
# TODO: Change this key in the end
app.config['SECRET_KEY'] = 'not a secure key'
Bootstrap(app)

db_name = 'timesheet.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

class HR(enum.Enum):
    valid = 1
    invalid = 2
    loginFail = 3

# Employee Table
class Employees(db.Model):
    __tablename__ = 'Employees'
    name = db.Column(db.String, primary_key=True)
    email = db.Column(db.String)
    password = db.Column(db.String)
    HR = db.Column(db.Integer) # 0 for not in HR, 1 for in HR

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

# Generates the list of names of employees for HRForm
def getNameChoices():
    choices = [('', '')]
    list = Employees.query.order_by(Employees.name).distinct()
    for data in list:
        choices.append((data.name, data.name))
    return choices

# HR Form
class HRForm(FlaskForm):
    name = SelectField(label='Name of the employee', 
        validators=[InputRequired()], choices=getNameChoices())
    dateBegin = DateField(label='First date you want your search to contain (formatted as mm/dd/yyyy)', 
        validators=[InputRequired()], format='%m/%d/%Y')
    dateEnd = DateField(label='Last date you want your search to contain (formatted as mm/dd/yyyy)', 
        validators=[InputRequired()], format='%m/%d/%Y')
    submit = SubmitField(label='Submit')

# Default route
@app.route('/')
def index():
    return render_template('index.html')

# Used in submitting hours, checks to see if the email and password are a valid login
def validLogin(e, password):
    list = Employees.query.filter_by(email=e).all()
    for data in list:
      if(data.password == password):
        return True, data.name
    return False, ''

# Hours Sumbission route
@app.route('/hours', methods=['GET', 'POST'])
def hours():
    form = HoursForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        # tup is a (bool, string) pair
        tup = validLogin(email, password)
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

# Used in HR login, checks to see if the email and password are a valid login
# If login is valid, checks to see if the person logging in is in HR
def validHR(e, password):
    list = Employees.query.filter_by(email=e).all()
    for data in list:
      if(data.password == password):
        if(data.HR):
            return HR.valid
        else:
            return HR.invalid
    return HR.loginFail

# HR Login route
@app.route('/hrlogin', methods=['GET', 'POST'])
def hrlogin():
    form = HRLoginForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        # TODO: Implement HR being able to view the database; regular employees cannot
        email = form.email.data
        password = form.password.data
        result = validHR(email, password)
        if result == HR.valid: # Valid login, in HR
            return redirect( url_for('hr'))
        elif result == HR.invalid: # Valid login, not in HR
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
        n = form.name.data
        dateBegin = form.dateBegin.data
        dateEnd = form.dateEnd.data
        filtered = []
        list = Timesheet.query.filter_by(name=n).order_by(Timesheet.date).all()
        for data in list:
            date = datetime.strptime(data.date, '%m/%d/%Y').date()
            if dateBegin <= date and date <= dateEnd:
                filtered.append(data)
        if len(filtered) == 0:
            message = 'There were no results found.'
        else:
            return redirect( url_for('hrresults', filtered=filtered))
    # If the user input something incorrectly, one of these errors will be printed                
    elif request.method == 'POST' and (not form.validate_on_submit()):
        message = 'Please formate the date(s) as mm/dd/yyyy.'
    return render_template('hr.html', form=form, message=message)

# HR Results route
@app.route('/hrresults/<filtered>', methods=['GET', 'POST'])
def hrresults(filtered):
    return render_template('hrresults.html', filtered=filtered)

if __name__ == '__main__':
    app.run()