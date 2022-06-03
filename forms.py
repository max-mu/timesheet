from wtforms import SubmitField, StringField, PasswordField, DateField, FloatField, HiddenField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    email = StringField(label='Email Address', validators=[DataRequired()])
    password = PasswordField(label='Password', validators=[DataRequired()])
    login = SubmitField(label='Login')

class HoursForm(FlaskForm):
    hours = FloatField(label='Hours you worked', validators=[DataRequired()])
    date = DateField(validators=[DataRequired()], format='%m/%d/%Y')
    approved = HiddenField()
    submit = SubmitField(label='Submit')