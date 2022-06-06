from wtforms import SubmitField, StringField, PasswordField, DateField, FloatField, HiddenField, SelectField, RadioField
from flask_wtf import FlaskForm
from wtforms.validators import InputRequired
from models import Employees

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
    choice = RadioField(validators=[InputRequired()], choices=[('hr', 'HR'), ('supv', 'Supervisor')])
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