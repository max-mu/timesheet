from flask import Flask, request, render_template, redirect, url_for
from forms import HRForm, HoursForm
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import enum

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
    approval = db.Column(db.String)

    def __init__(self, name, hours, date, approval):
        self.name = name
        self.hours = hours
        self.date = date
        self.approval = approval

class HR(enum.Enum):
    valid = 1
    invalid = 2
    loginFail = 3

def validLogin(e, password):
    list = Employee.query.filter_by(email=e).all()
    for data in list:
      if(data.password == password):
        return True, data.name
    return False, ''

def validHR(e, password):
    list = Employee.query.filter_by(email=e).all()
    for data in list:
      if(data.password == password):
        if(data.HR):
            return HR.valid
        else:
            return HR.invalid
    return HR.loginFail

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hours', methods=['GET', 'POST'])
def hours():
    form = HoursForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        email = form.email.data
        password = form.password.data
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
    elif request.method == 'POST' and (not form.validate_on_submit()):
        if not isinstance(form.hours.data, (int, float)):
            message = 'Please enter a numerical value for your hours.'
        else:
            message = 'Please formate the date as mm/dd/yyyy.'
    return render_template('hours.html', form=form, message=message)

@app.route('/hr', methods=['GET', 'POST'])
def hr():
    form = HRForm(request.form)
    message = ''
    if request.method == 'POST' and form.validate_on_submit():
        # TODO: Implement HR being able to view the database; regular employees cannot
        email = form.email.data
        password = form.password.data
        result = validHR(email, password)
        if result == HR.valid:
            return redirect( url_for('hours'))
        elif result == HR.invalid:
            message = 'You are not in the HR department. If you meant to submit your hours, go back and click on the correct link.'
        else:
            message = 'Invalid email/password.'
    return render_template('hr.html', form=form, message=message)

if __name__ == '__main__':
    app.run()