from wtforms import SubmitField, StringField, PasswordField, DateField
from wtforms import DecimalField, HiddenField, SelectField, RadioField, IntegerField
from flask_wtf import FlaskForm
from wtforms.validators import InputRequired, EqualTo
from models import Employees

# Hours Submission Form
class HoursForm(FlaskForm):
    id = HiddenField()
    email = StringField(label='Email Address', validators=[InputRequired()])
    password = PasswordField(label='Password', validators=[InputRequired()])
    date = DateField(label='Date', validators=[InputRequired()], format='%Y-%m-%d')
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
        choices=[('supv', 'Supervisor'), ('hr', 'HR')], default='supv')
    login = SubmitField(label='Login')

# Generates the list of names of employees for FetchForm
def get_name_choices():
    choices = [('', '')]
    list = Employees.query.order_by(Employees.name).distinct()
    for data in list:
        choices.append((data.name, data.name))
    return choices

# HR Search Form
class HRSearchForm(FlaskForm):
    name = SelectField(label='Name of the employee', 
        validators=[InputRequired()], choices=get_name_choices())
    dateBegin = DateField(label='First date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    dateEnd = DateField(label='Last date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    choice = RadioField(validators=[InputRequired()], 
        choices=[('csv', 'CSV'), ('browser', 'Browser')], default='csv')
    submit = SubmitField(label='Submit')

# Supervisor Fetch Form
class SupvSearchForm(FlaskForm):
    name = SelectField(label='Name of the employee', 
        validators=[InputRequired()], choices=get_name_choices())
    dateBegin = DateField(label='First date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    dateEnd = DateField(label='Last date you want your search to contain', 
        validators=[InputRequired()], format='%Y-%m-%d')
    submit = SubmitField(label='Submit')

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
    is_hr = IntegerField(label='Is HR', validators=[InputRequired()])
    supv = StringField(label='Supervisor Name')
    is_supv = IntegerField(label='Is Supervisor', validators=[InputRequired()])
    is_active = HiddenField()
    submit = SubmitField(label='Submit')