from wtforms import SubmitField, StringField, PasswordField, DateField, \
    DecimalField, SelectField
from wtforms_components import TimeField
from flask_wtf import FlaskForm
from wtforms.validators import InputRequired, EqualTo
from __init__ import mysql
from datetime import datetime
import pymysql

# Generates the list of names of employees for HRGeneralForm and SupvHoursForm
def get_name_choices(type, supv_id):
    choices = [('', ''), ('all', 'All employees')]
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    query = ''
    if type == 'hr':
        query = 'SELECT id, name FROM employees ORDER BY name'
    else:
        query = 'SELECT id, name FROM employees WHERE supv_id = \
            "%s" OR id = "%s" ORDER BY name'%(supv_id, supv_id)
    cur.execute(query)
    list = cur.fetchall()
    for data in list:
        choices.append((data['id'], data['name']))
    return choices

# Generates the list of supervisors for HREmployeesForm
def get_supvs():
    choices = [('-1', 'None')]
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    query = 'SELECT id, name FROM employees WHERE roles = "supv" \
        ORDER BY name'
    cur.execute(query)
    list = cur.fetchall()
    for data in list:
        choices.append((data['id'], data['name']))
    return choices

# Hours Submission Form
class HoursForm(FlaskForm):
    date = DateField(label='Date', 
        validators=[InputRequired()], format='%Y-%m-%d', default=datetime.now())
    clock_in = TimeField(label='Clock In')
    clock_out = TimeField(label='Clock Out')
    pto = DecimalField(label='Holiday/Paid Time Off', 
        validators=[InputRequired()], default=0)
    hours = DecimalField(label='Total Hours', validators=[InputRequired()])
    submit = SubmitField(label='Submit')

# Login Form
class LoginForm(FlaskForm):
    email = StringField(label='Email Address', validators=[InputRequired()])
    password = PasswordField(label='Password', validators=[InputRequired()])
    login = SubmitField(label='Login')

# HR Hours Search Form
class EmployHoursForm(FlaskForm):
    date_begin = DateField(label='First date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    date_end = DateField(label='Last date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    submit = SubmitField(label='Submit')

# HR Hours Search Form
class HRGeneralForm(FlaskForm):
    employ_id = SelectField(label='Name of the employee', 
        validators=[InputRequired()], choices=[])
    date_begin = DateField(label='First date you want your search to contain', 
        format='%Y-%m-%d')
    date_end = DateField(label='Last date you want your search to contain', 
        format='%Y-%m-%d')
    submit = SubmitField(label='Submit')

    def __init__(self, *args, **kwargs):
        super(HRGeneralForm, self).__init__(*args, **kwargs)
        self.employ_id.choices=get_name_choices('hr', None)


# HR Employees Form
class HREmployeeForm(FlaskForm):
    name = StringField(label='Name', validators=[InputRequired()])
    email = StringField(label='Email', validators=[InputRequired()])
    address = StringField(label='Address', validators=[InputRequired()])
    phone = StringField(label='Phone Number', validators=[InputRequired()])
    supv_id = SelectField(label='Supervisor Name', choices=[])
    roles = SelectField(label='Roles', 
        choices=[('none', 'None'), ('hr', 'HR'), ('supv', 'Supervisor')])
    submit = SubmitField(label='Submit')

    def __init__(self, *args, **kwargs):
        super(HREmployeeForm, self).__init__(*args, **kwargs)
        self.supv_id.choices=get_supvs()

# Supervisor Search Form
class SupvForm(FlaskForm):
    employ_id = SelectField(label='Name of the employee', 
        validators=[InputRequired()], choices=[])
    date_begin = DateField(label='First date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    date_end = DateField(label='Last date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    submit = SubmitField(label='Submit')

    def __init__(self, supv_id):
        super(SupvForm, self).__init__()
        self.employ_id.choices = get_name_choices('supv', supv_id)


# Onboarding Form
class OnboardingForm(FlaskForm):
    name = StringField(label='Name', validators=[InputRequired()])
    email = StringField(label='Email', validators=[InputRequired()])
    password = PasswordField(label='Password', validators=[InputRequired(), 
        EqualTo('confirm', message="The passwords don't match.")])
    confirm = PasswordField(label='Confirm Password', validators=[InputRequired()])
    address = StringField(label='Address', validators=[InputRequired()])
    phone = StringField(label='Phone Number', validators=[InputRequired()])
    submit = SubmitField(label='Submit')