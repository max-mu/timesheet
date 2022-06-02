from flask import Flask, request, flash, render_template, redirect, url_for
from forms import LoginForm, HoursForm
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'not a secure key'
Bootstrap(app)

db_name = 'timesheet.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

class Employee(db.Model):
    __tablename__ = 'Employees'
    name = db.Column(db.String, primary_key=True)
    email = db.Column(db.String)
    password = db.Column(db.String)
    HR = db.Column(db.Integer) # 0 for not in HR, 1 for in HR

class Timesheet(db.Model):
    __tablename__ = "Timesheet"
    name = db.Column(db.String, primary_key=True)
    hours = db.Column(db.Float)
    date = db.Column(db.String)

    def __init__(self, name, hours, date):
        self.name = name
        self.hours = hours
        self.date = date

def validLogin(e, password):
    list = Employee.query.filter_by(email=e).all()
    for data in list:
      if(data.password == password):
        return True, data.name
    return False, ''

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        # TODO: Implement HR being able to view the database; regular employees cannot
        email = form.email.data
        password = form.password.data
        tup = validLogin(email, password)
        if tup[0]:
            return redirect( url_for('hours', name=tup[1]))
        else:
            message = 'Invalid email/password.'
    return render_template('login.html', form=form, message=message)

@app.route('/hours/<name>', methods=['GET', 'POST'])
def hours(name):
    form = HoursForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        # TODO: Need to submit the name associated with the email and hours to a database
        return 'Your hours have been submitted!'
    elif request.method == 'POST' and (not form.validate_on_submit()):
        if not isinstance(form.hours.data, (int, float)):
            message = 'Please enter a numerical value for your hours.'
        else:
            message = 'Please formate the date as mm/dd/yyyy.'
    return render_template('hours.html', form=form, message=message)

if __name__ == '__main__':
    app.run()