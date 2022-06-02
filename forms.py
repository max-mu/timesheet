from wtforms import SubmitField, BooleanField, StringField, PasswordField, validators
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    email = StringField(label='Email Address', validators=[DataRequired()])
    password = PasswordField(label='Password', validators=[DataRequired()])
    login = SubmitField(label='Login')

class HoursForm(FlaskForm):
    hours = StringField(label='Hours you worked', validators=[DataRequired()])
    submit = SubmitField(label='Submit')