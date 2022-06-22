from wtforms import SubmitField, StringField, PasswordField, DateField, \
    DecimalField, HiddenField, SelectField, RadioField, IntegerField
from flask_wtf import FlaskForm
from wtforms.validators import InputRequired, EqualTo
from __init__ import mysql
from datetime import datetime
import pymysql

# Hours Submission Form
class HoursForm(FlaskForm):
    id = HiddenField()
    date = DateField(label='Date', 
        validators=[InputRequired()], format='%Y-%m-%d', default=datetime.now())
    clock_in = StringField(label='Clock In', validators=[InputRequired()])
    clock_out = StringField(label='Clock Out', validators=[InputRequired()])
    pto = DecimalField(label='Holiday/Paid Time Off', 
        validators=[InputRequired()], default=0)
    hours = DecimalField(label='Total Hours', validators=[InputRequired()])
    approved = HiddenField()
    submit = SubmitField(label='Submit')
    # Next two fields are to handle restoring the 'hours search' table 
    # in hours-results.html, not used in initial submission
    first_date = HiddenField()
    last_date = HiddenField()
    # Next field is to hold if user came from employee or supv search, not
    # used in inital submission
    type = HiddenField()

# Login Form
class LoginForm(FlaskForm):
    email = StringField(label='Email Address', validators=[InputRequired()])
    password = PasswordField(label='Password', validators=[InputRequired()])
    login = SubmitField(label='Login')

# Generates the list of names of employees for FetchForm
def get_name_choices(type, supv):
    choices = [('', ''), ('all', 'All employees')]
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    query = ''
    if type == 'hr':
        query = 'SELECT name FROM employees'
    else:
        query = 'SELECT name FROM employees WHERE supv = \
            "%s"'%(supv)
    cur.execute(query)
    list = cur.fetchall()
    for data in list:
        choices.append((data['name'], data['name']))
    return choices

# HR Hours Search Form
class EmployHoursForm(FlaskForm):
    date_begin = DateField(label='First date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    date_end = DateField(label='Last date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    submit = SubmitField(label='Submit')

# HR Hours Search Form
class HRGeneralForm(FlaskForm):
    name = SelectField(label='Name of the employee', 
        validators=[InputRequired()], choices=get_name_choices('hr', None))
    date_begin = DateField(label='First date you want your search to contain', 
        format='%Y-%m-%d')
    date_end = DateField(label='Last date you want your search to contain', 
        format='%Y-%m-%d')
    submit = SubmitField(label='Submit')

# HR Employees Form
class HREmployeeForm(FlaskForm):
    name = StringField(label='Name', validators=[InputRequired()])
    email = StringField(label='Email', validators=[InputRequired()])
    address = StringField(label='Address', validators=[InputRequired()])
    phone = StringField(label='Phone Number', validators=[InputRequired()])
    supv = StringField(label='Supervisor Name (leave blank if none)')
    roles = SelectField(label='Roles (leave blank if none)', 
        choices=[('', ''), ('hr', 'HR'), ('supv', 'Supervisor')])
    submit = SubmitField(label='Submit')

# Supervisor Hours Search Form
class SupvHoursForm(FlaskForm):
    name = SelectField(label='Name of the employee', 
        validators=[InputRequired()], choices=[])
    date_begin = DateField(label='First date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    date_end = DateField(label='Last date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    submit = SubmitField(label='Submit')

    def __init__(self, supv):
        super(SupvHoursForm, self).__init__()
        self.name.choices = get_name_choices('supv', supv)


# Onboarding Form
class OnboardingForm(FlaskForm):
    id = HiddenField()
    name = StringField(label='Name', validators=[InputRequired()])
    email = StringField(label='Email', validators=[InputRequired()])
    password = PasswordField(label='Password', validators=[InputRequired(), 
        EqualTo('confirm', message="The passwords don't match.")])
    confirm = PasswordField(label='Confirm Password', validators=[InputRequired()])
    address = StringField(label='Address', validators=[InputRequired()])
    phone = StringField(label='Phone Number', validators=[InputRequired()])
    supv = StringField(label='Supervisor Name')
    roles = StringField(label='Roles')
    submit = SubmitField(label='Submit')