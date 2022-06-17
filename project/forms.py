from wtforms import SubmitField, StringField, PasswordField, DateField, \
    DecimalField, HiddenField, SelectField, RadioField, IntegerField
from flask_wtf import FlaskForm
from wtforms.validators import InputRequired, EqualTo
from __init__ import mysql
import pymysql

# Hours Submission Form
class HoursForm(FlaskForm):
    id = HiddenField()
    date = DateField(label='Date', 
        validators=[InputRequired()], format='%Y-%m-%d')
    clock_in = StringField(label='Clock In', validators=[InputRequired()])
    clock_out = StringField(label='Clock Out', validators=[InputRequired()])
    pto = DecimalField(label='Holiday & Paid Time Off', 
        validators=[InputRequired()])
    hours = DecimalField(label='Total Hours', validators=[InputRequired()])
    approved = HiddenField()
    submit = SubmitField(label='Submit')

# Login Form
class LoginForm(FlaskForm):
    email = StringField(label='Email Address', validators=[InputRequired()])
    password = PasswordField(label='Password', validators=[InputRequired()])
    choice = RadioField(validators=[InputRequired()], 
        choices=[('hours', 'Submit/Adjust hours'), 
        ('supv', 'Login as supervisor'), ('hr', 'Login as HR')], default='hours')
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

# HR Search Form
class HRSearchForm(FlaskForm):
    name = SelectField(label='Name of the employee', 
        validators=[InputRequired()], choices=get_name_choices('hr', None))
    date_begin = DateField(label='First date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    date_end = DateField(label='Last date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    choice = RadioField(validators=[InputRequired()], 
        choices=[('csv', 'CSV'), ('browser', 'Browser')], default='csv')
    submit = SubmitField(label='Submit')

# Supervisor Fetch Form
class SupvSearchForm(FlaskForm):
    name = SelectField(label='Name of the employee', 
        validators=[InputRequired()], choices=[])
    date_begin = DateField(label='First date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    date_end = DateField(label='Last date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    submit = SubmitField(label='Submit')

    def __init__(self, supv):
        super(SupvSearchForm, self).__init__()
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